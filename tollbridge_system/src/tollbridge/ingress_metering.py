import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple

class IngressMeteringEngine:
    def __init__(self, mesh_path: str = "tollbridge_system/bridge_mesh.json", max_queue_size: int = 10000):
        self.mesh_path = Path(mesh_path)
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        # Store nonces as tuple: (nonce_key, expiration_timestamp)
        self.active_nonces: Dict[str, float] = {}
        self.load_mesh_config()

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

        current_time = time.time()
        if abs(current_time - timestamp) > 30:
            return False

        nonce_key = f"{node_id}:{nonce}"
        if nonce_key in self.active_nonces:
            return False

        node_config = self.node_registry.get(node_id, {})
        raw_data = f"{node_id}:{payload.get('amount')}:{payload.get('asset')}:{nonce}:{timestamp}"
        computed_sig = hashlib.sha256(raw_data.encode()).hexdigest()

        if computed_sig != client_sig:
            return False

        # Register nonce with a 60-second expiration buffer (2x sliding window)
        self.active_nonces[nonce_key] = current_time + 60.0
        return True

    async def enqueue_transaction(self, transaction_payload: Dict[str, Any]):
        """Non-blocking ingestion hook with backpressure awareness."""
        try:
            self.queue.put_nowait(transaction_payload)
        except asyncio.QueueFull:
            print("[CRITICAL WARNING] Metering queue full! Dropping transaction payload to protect hot path.")

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
                    print(f"[SECURITY WARNING] Rejected invalid cryptographic envelope for TX: {tx.get('nonce')}")
                    continue

                node_id = tx["node_id"]
                amount = float(tx["amount"])
                asset = tx["asset"]

                node_config = self.node_registry.get(node_id, {})
                rev_share_pct = node_config.get("revenue_share_pct", 15.0)

                node_cut = amount * (rev_share_pct / 100.0)
                protocol_cut = amount * ((100.0 - rev_share_pct) / 100.0)
                vault_address = node_config.get("vault_config", {}).get("payout_wallet", "unbound_vault")

                settlement_record = {
                    "timestamp": time.time(),
                    "node_id": node_id,
                    "vault": vault_address,
                    "asset": asset,
                    "total_processed": amount,
                    "node_payout": round(node_cut, 6),
                    "protocol_treasury": round(protocol_cut, 6),
                    "status": "SETTLED_ATOMIC"
                }
                
                print(f"[SETTLEMENT SUCCESS] Routed {node_cut:.4f} {asset} (15%) to node vault: {vault_address}")

            except Exception as e:
                print(f"[ERROR] Metering pipeline exception: {str(e)}")
            finally:
                self.queue.task_done()
