import os, sys, subprocess, json, tempfile
from pathlib import Path

def main():
    print("[P11] Starting Transient-Environment Resurrection Test...")
    repo_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip())
    evidence_dir = repo_root / "evidence" / "p11"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    print("[P11] Step 1: Packaging current repository state...")
    res_pkg = subprocess.run(["python3", str(repo_root / "tools/cell_runner.py"), "package"], capture_output=True, text=True)
    if res_pkg.returncode != 0:
        print(f"[ERROR] Packaging failed: {res_pkg.stderr}", file=sys.stderr)
        sys.exit(1)
        
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir) / "sovereign_resurrected"
        print(f"[P11] Step 2: Cloning repo to temp dir: {dest}")
        subprocess.run(["git", "clone", str(repo_root), str(dest)], check=True, capture_output=True)
        os.chdir(dest)
        
        print("[P11] Step 3: Verifying restored cell...")
        res_verify = subprocess.run(["python3", "tools/cell_runner.py", "verify"], capture_output=True, text=True)
        print(res_verify.stdout)
        if res_verify.returncode != 0:
            sys.exit(1)
            
        mutation_path = Path("experiments/mutations/test_mutation.json")
        mutation_path.parent.mkdir(parents=True, exist_ok=True)
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        import hmac, hashlib
        packet = {
            "mutation_id": "mut-p11-001",
            "parent_commit": head,
            "objective": "P11 test",
            "allowed_paths": ["tools/"],
            "allowed_commands": ["python3", "-c", "print('OK')"],
            "timeout_seconds": 5,
            "submission_policy": "local_only"
        }
        payload = {k: v for k, v in packet.items() if k != "signature"}
        packet["signature"] = hmac.new(b"sovereign_ephemeral_key_999", json.dumps(payload, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
        with open(mutation_path, "w") as f:
            json.dump(packet, f)
            
        print("[P11] Step 4: Running dry-run...")
        res_run = subprocess.run(["python3", "tools/cell_runner.py", "dry-run", "--mutation", str(mutation_path)], capture_output=True, text=True)
        print(res_run.stdout)
        if res_run.returncode != 0:
            sys.exit(1)
            
        print("[P11] Step 5: Running tests...")
        res_tests = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"], capture_output=True, text=True)
        print(res_tests.stdout)
        if res_tests.returncode != 0:
            sys.exit(1)
            
        os.chdir(repo_root)
        with open(evidence_dir / "resurrection_evidence.json", "w") as ef:
            json.dump({"p11_status": "COMPLETE"}, ef)
            
    plan_path = repo_root / "SOVEREIGN_SEED_MASTER_EXECUTION_PLAN.md"
    if plan_path.exists():
        content = plan_path.read_text()
        content = content.replace("| **P11** | RELEASE & RESTORATION | `NOT_STARTED`", "| **P11** | RELEASE & RESTORATION | `COMPLETE`")
        content = content.replace("| **P11** | RELEASE & RESTORATION | `FAILED_GATE`", "| **P11** | RELEASE & RESTORATION | `COMPLETE`")
        plan_path.write_text(content)
        
    print("[P11] COMPLETE")

if __name__ == "__main__":
    main()
