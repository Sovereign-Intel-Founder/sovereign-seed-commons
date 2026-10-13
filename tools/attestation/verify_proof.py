import json
import os
from hasher import generate_state_root

def verify():
    manifest_path = "evidence/manifests/latest_attestation.json"
    if not os.path.exists(manifest_path):
        print("ERROR: Manifest missing!")
        return False
    with open(manifest_path, "r") as f:
        data = json.load(f)
    current_root = generate_state_root()
    if data.get("state_root") == current_root:
        print(f"SUCCESS: Proof verified! Root: {current_root}")
        return True
    print("FAILURE: State root mismatch!")
    return False

if __name__ == "__main__":
    exit(0 if verify() else 1)
