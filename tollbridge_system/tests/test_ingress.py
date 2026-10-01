import asyncio
import time
import hashlib
import sys
from pathlib import Path

# Ensure src path is accessible
sys.path.append(str(Path("tollbridge_system/src").resolve()))
from tollbridge.ingress_metering import IngressMeteringEngine

async def run_integration_test():
    print("==================================================")
    print("[TEST SUITE] Starting Ingress Metering & Security Validation")
    print("==================================================")
    
    engine = IngressMeteringEngine("tollbridge_system/bridge_mesh.json")
    
    if not engine.node_registry:
        print("[ERROR] No nodes found in registry to test against.")
        return
        
    node_id = list(engine.node_registry.keys())[0]
    print(f"[TEST] Selected target node for simulation: {node_id}")

    # 1. Test Valid Transaction Payload
    amount = 1250.50
    asset = "USDC"
    nonce = f"nonce_{int(time.time() * 1000)}"
    timestamp = int(time.time())

    # Generate valid cryptographic signature matching engine format
    raw_data = f"{node_id}:{amount}:{asset}:{nonce}:{timestamp}"
    signature = hashlib.sha256(raw_data.encode()).hexdigest()

    valid_payload = {
        "node_id": node_id,
        "amount": amount,
        "asset": asset,
        "nonce": nonce,
        "timestamp": timestamp,
        "signature": signature
    }

    print("[TEST] Enqueuing valid cryptographically signed payload...")
    await engine.enqueue_transaction(valid_payload)

    # Spin up worker briefly to process queue
    worker_task = asyncio.create_task(engine.process_metering_loop())
    await asyncio.sleep(0.2)
    worker_task.cancel()

    # 2. Test Replay Attack Prevention
    print("[TEST] Verifying replay attack protection...")
    is_replay_valid = engine.verify_cryptographic_envelope(valid_payload)
    if not is_replay_valid:
        print("[SUCCESS] Replay attack successfully blocked (Nonce recognized).")
    else:
        print("[CRITICAL FAILURE] Replay attack was allowed!")
        sys.exit(1)

    # 3. Test Invalid Signature Rejection
    print("[TEST] Verifying invalid signature tamper rejection...")
    forged_payload = valid_payload.copy()
    forged_payload["nonce"] = f"nonce_{int(time.time() * 1000)}_forged"
    forged_payload["signature"] = "0000000000000000000000000000000000000000000000000000000000000000"
    
    is_forgery_valid = engine.verify_cryptographic_envelope(forged_payload)
    if not is_forgery_valid:
        print("[SUCCESS] Tampered payload successfully rejected.")
    else:
        print("[CRITICAL FAILURE] Tampered signature was accepted!")
        sys.exit(1)

    print("==================================================")
    print("[ALL TESTS PASSED] Ingress Metering & Security Verified.")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
