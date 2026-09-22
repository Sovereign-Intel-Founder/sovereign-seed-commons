import os
import json
import socket
import hmac
import hashlib
import sys
import signal
from pathlib import Path

SOCKET_PATH = "/tmp/sovereign_comm.sock"
LEDGER_PATH = Path("governance/voting_ledger.json")
SECRET = b"sovereign_seed_internal_secure_transit"

def load_authorized_keys() -> list:
    if not LEDGER_PATH.exists():
        print(f"[CRITICAL] Governance ledger missing at {LEDGER_PATH}.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(LEDGER_PATH, "r") as f:
            ledger = json.load(f)
        return list(ledger.get("weights", {}).keys())
    except Exception as e:
        print(f"[CRITICAL] Failed to parse voting ledger: {e}", file=sys.stderr)
        sys.exit(1)

def verify_signature(payload_bytes: bytes, signature: str, secret: bytes) -> bool:
    expected = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def cleanup(signum, frame):
    print("\n[COMM] Shutting down daemon, unlinking socket...")
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    sys.exit(0)

def run_daemon():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    authorized_identities = load_authorized_keys()
    print(f"[COMM] Authorized identities loaded: {authorized_identities}")
    
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
        
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(128) # Backlog queue for high concurrency
    os.chmod(SOCKET_PATH, 0o600)
    
    print(f"[COMM] Hardened ingestion daemon active on domain socket: {SOCKET_PATH}")
    
    while True:
        try:
            conn, _ = server.accept()
        except socket.error:
            continue
            
        with conn:
            try:
                conn.settimeout(5.0)
                raw_data = conn.recv(65536)
                if not raw_data:
                    continue
                    
                packet = json.loads(raw_data.decode("utf-8"))
                sender = packet.get("sender")
                signature = packet.get("signature")
                payload = packet.get("payload")
                
                if sender not in authorized_identities:
                    conn.sendall(b"ERROR: UNAUTHORIZED_SENDER")
                    continue
                    
                payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
                if not signature or not verify_signature(payload_bytes, signature, SECRET):
                    conn.sendall(b"ERROR: INVALID_SIGNATURE")
                    continue
                    
                queue_dir = Path("experiments/queue")
                queue_dir.mkdir(parents=True, exist_ok=True)
                objective_id = payload.get("objective_id", "obj-unknown")
                
                # Atomic write pattern: write to tmp then rename
                tmp_path = queue_dir / f".{objective_id}.tmp"
                target_path = queue_dir / f"{objective_id}.json"
                
                with open(tmp_path, "w") as qf:
                    json.dump(payload, qf, indent=2)
                tmp_path.rename(target_path)
                
                print(f"[SUCCESS] Objective {objective_id} atomically ingested from {sender}.")
                conn.sendall(b"SUCCESS: OBJECTIVE_COMMITTED")
                
            except Exception as e:
                print(f"[ERROR] Ingestion fault: {e}", file=sys.stderr)
                try:
                    conn.sendall(b"ERROR: MALFORMED_PACKET")
                except:
                    pass

if __name__ == "__main__":
    run_daemon()
