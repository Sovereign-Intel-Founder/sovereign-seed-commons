import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, Any

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
import base58

class IngressMeteringEngine:
    def __init__(self, mesh_path: str = "tollbridge_system/bridge_mesh.json", max_queue_size: int = 10000):
        self.mesh_path = Path(mesh_path)
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.active_nonces: Dict[str, float] = {}
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.load_mesh_config()
        
        # Load hot ingress keypair for live mainnet transaction dispatching
        secret_key_b58 = os.getenv("INGRESS_HOT_WALLET_PRIVATE_KEY", "")
        if secret_key_b58:
            try:
                self.hot_wallet = Keypair.from_bytes(base58.b58decode(secret_key_b58))
            except Exception:
                self.hot_wallet = None
        else:
            self.hot_wallet = None

    def load_mesh_config(self):
        if self.mesh_path.exists():
            data = json.loads(self.mesh_path.read_text())
            nodes = data if isinstance(data, list) else data.get("nodes", [data])
            self.node_registry = {
                n.get("id", n.get("node_id", "edge_node")): n for n in nodes
            }
        else:
            self.node_registry = {}

    def _prune_expired_nonces(self):
        """Removes expired nonces from memory to prevent memory leaks."""
        current_time = time.time()
        expired_keys = [k for k, exp in self.active_nonces.items() if exp < current_time]
        for k in expired_keys:
            del self.active_nonces[k]

    def verify_cryptographic_envelope(self, payload: Dict[str, Any]) -> bool:
        """Validates SHA-256 signature, 30-second sliding window, and purges stale nonces."""
        self._prune_expired_nonces()
        node_id = payload.get("node_id")
        nonce = payload.get("nonce")
        timestamp = payload.get("timestamp", 0)
        client_sig = payload.get("signature")

        if abs(time.time() - timestamp) > 30:
            return False

        nonce_key = f"{node_id}:{nonce}"
        if nonce_key in self.active_nonces:
            return False

        raw_data = f"{node_id}:{payload.get('amount')}:{payload.get('asset')}:{nonce}:{timestamp}"
        computed_sig = hashlib.sha256(raw_data.encode()).hexdigest()

        if computed_sig != client_sig:
            return False

        self.active_nonces[nonce_key] = time.time() + 60.0
        return True

    async def enqueue_transaction(self, transaction_payload: Dict[str, Any]):
        """Non-blocking ingestion hook with backpressure awareness."""
        try:
            self.queue.put_nowait(transaction_payload)
        except asyncio.QueueFull:
            print("[CRITICAL WARNING] Metering queue full! Dropping transaction payload to protect hot path.")

    async def dispatch_onchain_settlement(self, vault_pubkey_str: str, node_cut: float, asset: str):
        """Dispatches live mainnet transfer for the node's 15% cut."""
        if not self.hot_wallet or asset != "SOL":
            print(f"[SIMULATION / OFFLINE] Logged {node_cut} {asset} split for vault {vault_pubkey_str}")
            return

        client = AsyncClient(self.rpc_url)
        try:
            recipient = Pubkey.from_string(vault_pubkey_str)
            lamports = int(node_cut * 1_000_000_000)  # Convert SOL to lamports
            
            recent_blockhash = (await client.get_latest_blockhash()).value.blockhash
            
            ix = transfer(TransferParams(
                from_pubkey=self.hot_wallet.pubkey(),
                to_pubkey=recipient,
                lamports=lamports
            ))
            
            msg = MessageV0.try_compile(
                payer=self.hot_wallet.pubkey(),
                instructions=[ix],
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash
            )
            
            tx = VersionedTransaction(msg, [self.hot_wallet])
            result = await client.send_transaction(tx)
            print(f"[MAINNET SETTLEMENT SUCCESS] Tx Signature: {result.value}")
        except Exception as e:
            print(f"[MAINNET ERROR] Failed to broadcast settlement: {str(e)}")
        finally:
            await client.close()

    async def process_metering_loop(self):
        """Asynchronous background worker handling settlement calculations."""
        while True:
            try:
                tx = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                if not self.verify_cryptographic_envelope(tx):
                    print(f"[SECURITY WARNING] Rejected invalid cryptographic envelope: {tx.get('nonce')}")
                    continue

                node_id = tx["node_id"]
                amount = float(tx["amount"])
                asset = tx["asset"]

                node_config = self.node_registry.get(node_id, {})
                rev_share_pct = node_config.get("revenue_share_pct", 15.0)

                node_cut = amount * (rev_share_pct / 100.0)
                vault_address = node_config.get("vault_config", {}).get("payout_wallet", "")

                if vault_address and not vault_address.startswith("vault_acc_"):
                    await self.dispatch_onchain_settlement(vault_address, node_cut, asset)
                else:
                    print(f"[SETTLEMENT LOG] Local accounting recorded {node_cut:.4f} {asset} for {node_id}")

            except Exception as e:
                print(f"[ERROR] Metering pipeline exception: {str(e)}")
            finally:
                self.queue.task_done()
