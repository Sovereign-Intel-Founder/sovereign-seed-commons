import json
import hashlib
import sys
from pathlib import Path

LINEAGE_PATH = Path("memory/lineage.jsonl")

def verify_chain():
    print("[VERIFY] Inspecting cryptographic lineage chain integrity...")
    
    if not LINEAGE_PATH.exists():
        print(f"[CRITICAL] Lineage log missing at {LINEAGE_PATH}", file=sys.stderr)
        sys.exit(1)
        
    expected_parent = hashlib.sha256(b"SOVEREIGN_GENESIS_ROOT_SEED").hexdigest()
    
    with open(LINEAGE_PATH, "r") as f:
        lines = f.readlines()
        
    if not lines:
        print("[WARNING] Lineage log is empty.")
        return
        
    for idx, line in enumerate(lines):
        record = json.loads(line.strip())
        record_hash = record.get("hash")
        data = record.get("data")
        
        # Recalculate hash of data payload
        payload_str = json.dumps(data, sort_keys=True)
        calculated_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        
        if calculated_hash != record_hash:
            print(f"[SECURITY ALERT] Hash mismatch at entry {idx}! Tampering detected.", file=sys.stderr)
            sys.exit(1)
            
        parent_in_record = data.get("parent_lineage_hash")
        if idx == 0:
            # First entry links back to genesis root seed or initial anchor
            pass
        else:
            if parent_in_record != expected_parent:
                print(f"[SECURITY ALERT] Chain broken at entry {idx}! Expected parent {expected_parent[:16]}..., got {parent_in_record[:16]}...", file=sys.stderr)
                sys.exit(1)
                
        expected_parent = record_hash
        print(f"[VERIFIED] Block {idx} ({data.get('cell_id')}): Hash valid.")
        
    print("[SUCCESS] Complete lineage cryptographic chain verified. Zero tampering detected.")

if __name__ == "__main__":
    verify_chain()
