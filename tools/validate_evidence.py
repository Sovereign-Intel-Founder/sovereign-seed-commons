import json
import sys
from pathlib import Path

def validate_evidence():
    manifest_path = Path("experiments/manifests/latest_proposal.json")
    if not manifest_path.exists():
        print("[ERROR] Evidence manifest missing: latest_proposal.json not found.")
        sys.exit(1)
    
    with open(manifest_path, "r") as f:
        data = json.load(f)
    
    required_fields = ["proposal_id", "status", "timestamp", "tests_passed"]
    for field in required_fields:
        if field not in data:
            print(f"[ERROR] Evidence manifest invalid: missing required field '{field}'.")
            sys.exit(1)
            
    if not data.get("tests_passed"):
        print("[ERROR] Evidence check failed: tests_passed is False.")
        sys.exit(1)
        
    print("[SUCCESS] Evidence manifest verified. Proposal is structurally sound.")

if __name__ == "__main__":
    validate_evidence()
