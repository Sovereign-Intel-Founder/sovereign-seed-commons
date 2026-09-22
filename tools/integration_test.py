import subprocess
import time
import socket
import json
import hmac
import hashlib
import os
import signal
from pathlib import Path

SOCKET_PATH = "/tmp/sovereign_comm.sock"
SECRET = b"sovereign_seed_internal_secure_transit"

def run_integration_test():
    print("[TEST] Initializing Sovereign Seed Commons end-to-end integration suite...")
    
    # 1. Verify Governance Ledger
    ledger_path = Path("governance/voting_ledger.json")
    assert ledger_path.exists(), "Voting ledger missing!"
    with open(ledger_path, "r") as f:
        ledger = json.load(f)
    assert "@joshua445" in ledger["weights"], "Founder key missing!"
    print("[PASSED] Governance ledger and founder weights verified.")
    
    # 2. Start Communication Daemon in Background
    daemon = subprocess.Popen(["python3", "tools/communication_daemon.py"])
    time.sleep(1.5) # Wait for socket bind
    
    try:
        # Test Socket Ingestion & HMAC Auth
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SOCKET_PATH)
        
        payload = {
            "objective_id": "obj-integration-001",
            "action": "verify_lineage",
            "parameters": {"target": "memory/"}
        }
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(SECRET, payload_bytes, hashlib.sha256).hexdigest()
        
        packet = {
            "sender": "@joshua445",
            "signature": sig,
            "payload": payload
        }
        
        client.sendall(json.dumps(packet).encode("utf-8"))
        response = client.recv(1024)
        client.close()
        
        print(f"Daemon Response: {response.decode('utf-8')}")
        assert response == b"SUCCESS: OBJECTIVE_COMMITTED", "Daemon failed objective commitment."
        print("[PASSED] Phase P10 Communication daemon ingestion verified.")
        
    finally:
        daemon.send_signal(signal.SIGINT)
        daemon.wait()
        
    # 3. Test Migration and Resurrection Engine
    print("[TEST] Running state export and resurrection cycle...")
    export_res = subprocess.run(["python3", "tools/resurrection.py"], capture_output=True, text=True)
    assert export_res.returncode == 0, f"Resurrection export failed: {export_res.stderr}"
    
    resurrect_res = subprocess.run(["python3", "tools/resurrection.py", "resurrect", "/tmp/sovereign_live_test"], capture_output=True, text=True)
    assert resurrect_res.returncode == 0, f"Resurrection extraction failed: {resurrect_res.stderr}"
    print("[PASSED] Phase P11 Migration and secure resurrection cycle verified.")
    
    print("\n[SUCCESS] ALL INTEGRATION TESTS PASSED. SYSTEM READY FOR EXTERNAL CELLS.")

if __name__ == "__main__":
    run_integration_test()
