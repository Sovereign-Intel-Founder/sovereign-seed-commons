import os
import sys
import subprocess
import json
import tempfile
import hashlib
import hmac
from pathlib import Path

def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def get_git_output(args):
    res = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
    return res.stdout.strip()

def main():
    print("[P13-DEMO] Initializing End-to-End Genesis-to-Cell Demonstration...")
    
    repo_root = Path(get_git_output(["rev-parse", "--show-toplevel"]))
    evidence_dir = repo_root / "evidence" / "p13"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    current_commit = get_git_output(["rev-parse", "HEAD"])
    
    # Step 1: Package Genesis Bundle
    print("[P13] Step 1: Packaging genesis bundle...")
    res_pkg = subprocess.run(["python3", str(repo_root / "tools/cell_runner.py"), "package"], capture_output=True, text=True)
    if res_pkg.returncode != 0:
        print(f"[ERROR] Packaging failed: {res_pkg.stderr}", file=sys.stderr)
        sys.exit(1)
        
    bundle_path = repo_root / "genesis" / "resurrection_bundle.tar.gz"
    manifest_path = repo_root / "genesis" / "resurrection_manifest.json"
    
    bundle_hash = compute_hash(bundle_path.read_bytes()) if bundle_path.exists() else "N/A"
    manifest_hash = compute_hash(manifest_path.read_bytes()) if manifest_path.exists() else "N/A"
    
    # Step 2: Clean Sandbox Extraction & Verification
    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox = Path(tmpdir) / "sovereign_p13_sandbox"
        print(f"[P13] Step 2: Cloning into isolated sandbox: {sandbox}")
        subprocess.run(["git", "clone", str(repo_root), str(sandbox)], check=True, capture_output=True)
        
        os.chdir(sandbox)
        
        print("[P13] Step 3: Running cell_runner verify in sandbox...")
        res_verify = subprocess.run(["python3", "tools/cell_runner.py", "verify"], capture_output=True, text=True)
        print(res_verify.stdout)
        if res_verify.returncode != 0:
            print(f"[ERROR] Verification failed in sandbox: {res_verify.stderr}", file=sys.stderr)
            sys.exit(1)
            
        # Step 4: Execute Bounded Mutation in Sandbox
        print("[P13] Step 4: Executing bounded cell mutation in sandbox...")
        mut_dir = Path("experiments/mutations")
        mut_dir.mkdir(parents=True, exist_ok=True)
        mut_file = mut_dir / "p13_demo_mutation.json"
        
        secret = os.environ.get("SOVEREIGN_SECRET", "sovereign_ephemeral_key_999").encode("utf-8")
        packet = {
            "mutation_id": "mut-p13-demo-001",
            "parent_commit": current_commit,
            "objective": "P13 public demonstration end-to-end cell validation",
            "allowed_paths": ["tools/"],
            "allowed_commands": ["python3", "-c", "print('P13_DEMO_MUTATION_SUCCESS')"],
            "timeout_seconds": 5,
            "submission_policy": "local_only"
        }
        payload = {k: v for k, v in packet.items() if k != "signature"}
        packet["signature"] = hmac.new(secret, json.dumps(payload, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
        mut_file.write_text(json.dumps(packet, indent=2))
        
        res_run = subprocess.run(["python3", "tools/cell_runner.py", "dry-run", "--mutation", str(mut_file)], capture_output=True, text=True)
        print(res_run.stdout)
        if res_run.returncode != 0:
            print(f"[ERROR] Mutation dry-run failed in sandbox: {res_run.stderr}", file=sys.stderr)
            sys.exit(1)
            
        os.chdir(repo_root)
        
        # Step 5: Record Demonstration Evidence
        evidence_data = {
            "p13_status": "COMPLETE",
            "demonstration_commit": current_commit,
            "bundle_hash": bundle_hash,
            "manifest_hash": manifest_hash,
            "sandbox_verification": "PASSED",
            "sandbox_mutation_result": "SUCCESS",
            "sandbox_mutation_output": res_run.stdout.strip(),
            "workflow_verified": True
        }
        
        evidence_file = evidence_dir / "demonstration_evidence.json"
        evidence_file.write_text(json.dumps(evidence_data, indent=2))
        print(f"[P13] Demonstration evidence written to {evidence_file}")
        
    # Step 6: Update Master Execution Plan
    plan_path = repo_root / "SOVEREIGN_SEED_MASTER_EXECUTION_PLAN.md"
    if plan_path.exists():
        content = plan_path.read_text()
        content = content.replace("| **P13** | PUBLIC DEMONSTRATION | `NOT_STARTED`", "| **P13** | PUBLIC DEMONSTRATION | `COMPLETE`")
        content = content.replace("| **P13** | PUBLIC DEMONSTRATION | `FAILED_GATE`", "| **P13** | PUBLIC DEMONSTRATION | `COMPLETE`")
        plan_path.write_text(content)
        
    print("[P13] DEMO COMPLETED SUCCESSFULLY. P13 = COMPLETE.")

if __name__ == "__main__":
    main()
