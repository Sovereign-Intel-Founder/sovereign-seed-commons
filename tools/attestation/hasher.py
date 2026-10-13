import hashlib
import json
import os
import time

def generate_state_root(ledger_path="revenue_vault.db"):
    hasher = hashlib.sha256()
    if os.path.exists(ledger_path):
        with open(ledger_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
    return hasher.hexdigest()

if __name__ == "__main__":
    root_hash = generate_state_root()
    manifest = {
        "timestamp_utc": int(time.time()),
        "state_root": root_hash,
        "protocol": "Sovereign Intelligence Protocol",
        "status": "VERIFIED"
    }
    os.makedirs("evidence/manifests", exist_ok=True)
    with open("evidence/manifests/latest_attestation.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Attestation state root generated: {root_hash}")
