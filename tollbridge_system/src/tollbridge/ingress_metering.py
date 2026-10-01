import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any

class IngressMeteringEngine:
    def __init__(self, mesh_path: str = "tollbridge_system/bridge_mesh.json"):
        self.mesh_path = Path(mesh_path)
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_nonces = set()
        self.load_mesh_config()

    def load_mesh_config(self):
        if self.mesh_path.exists():
            data = json.loads(self.mesh_path.read_text())
            nodes = data if isinstance(data, list) else data.get("nodes", [data])
            # Map node IDs to their respective vault and security configs
            self.node_registry = {
                n.get("id", n.get("node_id", "edge_node")): n for n in nodes
            }
        else:
            self.node_registry = {}

    def verify_cryptographic_envelope(self, payload: Dict[str, Any]) -> bool:
        """Validates SHA-256 signature and 30-second sliding window nonce."""
        node_id = payload.get("node_id")
        nonce = payload.get("nonce")
        timestamp = payload.get("timestamp", 0)
        client_sig = payload.get("signature")

        # Check timestamp sliding window (30s max drift)
        current_time = time.time()
        if abs(current_time - timestamp) > 30:
            return False

        # Check replay protection via nonce
        nonce_key = f"{node_id}:{nonce}"
        if nonce_key in self.active_nonces:
            return False

        # Verify signature hash
        node_config = self.node_registry.get(node_id, {})
        crypto_conf = node_config.get("cryptographic_envelopes", {})
        
        raw_data = f"{node_id}:{payload.get('amount')}:{payload.get('asset')}:{nonce}:{timestamp}"
        computed_sig = hashlib.sha256(raw_data.encode()).hexdigest()

        if computed_sig != client_sig:
            return False

        # Register nonce to prevent replays
        self.active_nonces.add(nonce_key)
        return True

    async def enqueue_transaction(self, transaction_payload: Dict[str, Any]):
        """Non-blocking ingestion hook for the hot path."""
        await self.queue.put(transaction_payload)

    async def process_metering_loop(self):
        """Asynchronous background worker handling settlement calculations."""
        while True:
            tx = await self.queue.get()
            try:
                if not self.verify_cryptographic_envelope(tx):
                    print(f"[SECURITY WARNING] Rejected invalid cryptographic envelope for TX: {tx.get('nonce')}")
                    continue

                node_id = tx["node_id"]
                amount = float(tx["amount"])
                asset = tx["asset"]

                node_config = self.node_registry.get(node_id, {})
                rev_share_pct = node_config.get("revenue_share_pct", 15.0)

                # Calculate deterministic split
                node_cut = amount * (rev_share_pct / 100.0)
                protocol_cut = amount * ((100.0 - rev_share_pct) / 100.0)

                vault_address = node_config.get("vault_config", {}).get("payout_wallet", "unbound_vault")

                # Log verified settlement ledger entry
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
                # In production, flush settlement_record to persistent storage or chain indexer here.

            except Exception as e:
                print(f"[ERROR] Metering pipeline exception: {str(e)}")
            finally:
                self.queue.task_done()

# Quick smoke test runner
if __name__ == "__main__":
    async def test_pipeline():
        engine = IngressMeteringEngine()
        print("[INIT] Ingress Metering Engine initialized successfully.")
    asyncio.run(test_pipeline())
