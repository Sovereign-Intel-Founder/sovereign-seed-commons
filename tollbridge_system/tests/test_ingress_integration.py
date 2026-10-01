import asyncio
import os
import shutil
import tempfile
from solders.keypair import Keypair
from tollbridge.ingress_metering import IngressMeteringEngine
from tollbridge.security import verify_production_safety

async def run_integration_test():
    print("--- INITIALIZING INGRESS INTEGRATION TEST ---")
    
    # Use a temporary database for the test vault
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    try:
        engine = IngressMeteringEngine(db_path=db_path, max_queue_depth=10, batch_size=5)
        await engine.start()
        
        # 1. Generate real Ed25519 keypair using solders/nacl
        signer = Keypair()
        pubkey_str = str(signer.pubkey())
        
        payload = b"SIP_COLLOSSEUM_TELEMETRY_PAYLOAD_V1"
        signature_bytes = signer.sign_message(payload)
        signature_hex = bytes(signature_bytes).hex()
        nonce = "nonce_alpha_001"
        
        # 2. Test Normal Acceptance & Enqueue
        res = await engine.submit_payload(
            client_pubkey=pubkey_str,
            raw_payload=payload,
            signature_hex=signature_hex,
            nonce=nonce,
            asset_type="SOL"
        )
        print(f"-> Payload Submission Result: {res}")
        assert res["status"] == "accepted", f"Expected accepted, got {res}"
        
        # 3. Test Nonce Replay Protection (Duplicate Nonce)
        res_replay = await engine.submit_payload(
            client_pubkey=pubkey_str,
            raw_payload=payload,
            signature_hex=signature_hex,
            nonce=nonce,
            asset_type="SOL"
        )
        print(f"-> Nonce Replay Result: {res_replay}")
        assert res_replay["status"] == "rejected" and res_replay["code"] == 409, "Nonce replay not blocked!"
        
        # 4. Test Payload Size Hardening (> 64KB)
        oversized_payload = b"A" * 70000
        res_size = await engine.submit_payload(
            client_pubkey=pubkey_str,
            raw_payload=oversized_payload,
            signature_hex=signature_hex,
            nonce="nonce_beta_002",
            asset_type="SOL"
        )
        print(f"-> Oversized Payload Result: {res_size}")
        assert res_size["status"] == "rejected" and res_size["code"] == 413, "Payload size limit not enforced!"
        
        # 5. Allow background WAL writer worker time to flush batch to disk
        await asyncio.sleep(1.0)
        await engine.stop()
        
        # 6. Verify SQLite Persistence
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT client_pubkey, asset_type, payload_size_bytes, nonce FROM ingress_telemetry;")
        rows = cursor.fetchall()
        conn.close()
        
        print(f"-> Vault Records Flushed to Disk: {rows}")
        assert len(rows) == 1, f"Expected 1 record in vault, found {len(rows)}"
        assert rows[0][3] == nonce, "Persisted nonce does not match!"
        
        print("--- ALL INTEGRATION & PERSISTENCE TESTS PASSED CLEANLY ---")
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(run_integration_test())
