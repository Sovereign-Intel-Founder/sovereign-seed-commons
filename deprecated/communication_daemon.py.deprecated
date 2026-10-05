import os
import json
import socket
import hmac
import hashlib
import sys
import signal
import re
from pathlib import Path
from datetime import datetime, timezone

SOCKET_PATH = "/tmp/sovereign_comm.sock"
LEDGER_PATH = Path("governance/voting_ledger.json")

SECRET = os.environ.get("SOVEREIGN_COMM_SECRET", "").encode("utf-8")
OBJECTIVE_ID_REGEX = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
MAX_CLOCK_SKEW_SECONDS = 60

def load_ledger_weights() -> dict:
    if not LEDGER_PATH.exists():
        print(f"[CRITICAL] Governance ledger missing at {LEDGER_PATH}.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(LEDGER_PATH, "r") as f:
            ledger = json.load(f)
        return ledger.get("weights", {})
    except Exception as e:
        print(f"[CRITICAL] Failed to parse voting ledger: {e}", file=sys.stderr)
        sys.exit(1)

def verify_signature(payload_bytes: bytes, signature: str, secret: bytes) -> bool:
    if not secret:
        return False
    expected = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def cleanup(signum, frame):
    print("\n[COMM] Shutting down daemon, unlinking socket...")
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    sys.exit(0)

def run_daemon():
    if not SECRET:
        print("[CRITICAL] SOVEREIGN_COMM_SECRET environment variable not set. Aborting securely.", file=sys.stderr)
        sys.exit(1)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    weights = load_ledger_weights()
    print(f"[COMM] Authorized voting weights loaded for: {list(weights.keys())}")
    
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
        
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(128)
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
                
                # 1. Verify Sender has Active Voting Weight (> 0)
                if sender not in weights or weights[sender] <= 0:
                    conn.sendall(b"ERROR: ZERO_OR_UNAUTHORIZED_WEIGHT")
                    continue
                
                # 2. Enforce Timestamp Freshness (Replay Attack Prevention)
                pkt_timestamp = payload.get("timestamp")
                if not pkt_timestamp:
                    conn.sendall(b"ERROR: MISSING_TIMESTAMP")
                    continue
                
                try:
                    pkt_dt = datetime.strptime(pkt_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    now_dt = datetime.now(timezone.utc)
                    delta_seconds = abs((now_dt - pkt_dt).total_seconds())
                    if delta_seconds > MAX_CLOCK_SKEW_SECONDS:
                        conn.sendall(b"ERROR: PACKET_EXPIRED_OR_FUTURE")
                        continue
                except ValueError:
                    conn.sendall(b"ERROR: MALFORMED_TIMESTAMP")
                    continue

                objective_id = payload.get("objective_id", "")
                if not OBJECTIVE_ID_REGEX.match(objective_id):
                    conn.sendall(b"ERROR: MALFORMED_OBJECTIVE_ID")
                    continue
                    
                payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
                if not signature or not verify_signature(payload_bytes, signature, SECRET):
                    conn.sendall(b"ERROR: INVALID_SIGNATURE")
                    continue
                    
                queue_dir = Path("experiments/queue")
                queue_dir.mkdir(parents=True, exist_ok=True)
                
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
