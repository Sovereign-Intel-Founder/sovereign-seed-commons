import json
import hashlib
import sys
import os

def verify_lineage(file_path="lineage_memory.json"):
    if not os.path.exists(file_path):
        print(f"❌ Error: Lineage file '{file_path}' not found.")
        sys.exit(1)

    with open(file_path, "r") as f:
        chain = json.load(f)

    if not isinstance(chain, list) or len(chain) == 0:
        print("❌ Error: Invalid or empty lineage chain.")
        sys.exit(1)

    expected_prev = "0000000000000000000000000000000000000000000000000000000000000000"

    for idx, entry in enumerate(chain):
        stored_hash = entry.get("hash")
        prev_hash = entry.get("prev_hash")

        if prev_hash != expected_prev:
            print(f"[SECURITY ALERT] Prev hash mismatch at entry {idx}!")
            sys.exit(1)

        # Re-compute hash using canonical JSON formatting
        entry_copy = {k: v for k, v in entry.items() if k != "hash"}
        canonical_bytes = json.dumps(entry_copy, sort_keys=True).encode('utf-8')
        computed_hash = hashlib.sha256(canonical_bytes).hexdigest()

        if computed_hash != stored_hash:
            print(f"[SECURITY ALERT] Hash mismatch at entry {idx}! Stored: {stored_hash}, Computed: {computed_hash}")
            sys.exit(1)

        expected_prev = stored_hash

    print("✅ Lineage verification passed: Hash chain integrity confirmed.")

if __name__ == "__main__":
    verify_lineage()
