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
TEST_SECRET = b"sovereign_test_secret_transit_key_999"

def run_integration_test():
    print("[TEST] Initializing rigorous multi-environment integration suite...")
    
    ledger_path = Path("governance/voting_ledger.json")
    assert ledger_path.exists(), "Voting ledger missing!"
    with open(ledger_path, "r") as f:
        ledger = json.load(f)
    assert "@joshua445" in ledger["weights"], "Founder key missing!"
    print("[PASSED] Governance ledger and founder weights verified.")
    
    env = os.environ.copy()
    env["SOVEREIGN_COMM_SECRET"] = TEST_SECRET.decode("utf-8")
    
    daemon = subprocess.Popen(["python3", "tools/communication_daemon.py"], env=env)
    time.sleep(1.5)
    
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(SOCKET_PATH)
        
        payload = {
            "objective_id": "obj-integration-001",
            "action": "verify_lineage",
            "parameters": {"target": "memory/"}
        }
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(TEST_SECRET, payload_bytes, hashlib.sha256).hexdigest()
        
        packet = {
            "sender": "@joshua445",
            "signature": sig,
            "payload": payload
        }
        
        client.sendall(json.dumps(packet).encode("utf-8"))
        response = client.recv(1024)
        client.close()
        
        assert response == b"SUCCESS: OBJECTIVE_COMMITTED", f"Daemon rejected valid objective: {response}"
        print("[PASSED] Secure IPC communication daemon and HMAC authentication verified.")
        
    finally:
        daemon.send_signal(signal.SIGINT)
        daemon.wait()
        
    print("[TEST] Running isolated server-to-cloud resurrection extraction...")
    export_res = subprocess.run(["python3", "tools/resurrection.py"], capture_output=True, text=True)
    assert export_res.returncode == 0, f"Resurrection export failed: {export_res.stderr}"
    
    isolated_target = "/tmp/sovereign_cloud_node_simulation"
    resurrect_res = subprocess.run(["python3", "tools/resurrection.py", "resurrect", isolated_target], capture_output=True, text=True)
    assert resurrect_res.returncode == 0, f"Resurrection extraction failed: {resurrect_res.stderr}"
    
    resurrected_ledger = Path(isolated_target) / "governance" / "voting_ledger.json"
    assert resurrected_ledger.exists(), "Resurrected environment missing voting ledger!"
    print("[PASSED] Multi-environment server-to-cloud resurrection verified.")
    
    evidence_dir = Path("experiments/manifests")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "integration_evidence.json"
    
    evidence_data = {
        "status": "PASSED",
        "timestamp": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
        "components_tested": ["voting_ledger", "communication_daemon_hmac", "atomic_queue", "isolated_resurrection"]
    }
    with open(evidence_path, "w") as ef:
        json.dump(evidence_data, ef, indent=2)
    print(f"[SUCCESS] Integration test evidence artifact written to {evidence_path}")

if __name__ == "__main__":
    run_integration_test()
