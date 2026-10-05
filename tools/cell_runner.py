import os
import sys
import subprocess
import json
import hashlib
import hmac
import tarfile
from pathlib import Path

def get_secret():
    if "SOVEREIGN_SECRET" not in os.environ:
        print("[ERROR] SOVEREIGN_SECRET environment variable not set. Failing safely.", file=sys.stderr)
        sys.exit(1)
    return os.environ["SOVEREIGN_SECRET"].encode("utf-8")

def verify_clean_checkout():
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    if res.stdout.strip():
        print("[ERROR] Dirty checkout detected: uncommitted changes or untracked files present.", file=sys.stderr)
        sys.exit(1)

def verify_mutation(mutation_path):
    secret = get_secret()
    data = json.loads(Path(mutation_path).read_text())
    sig = data.pop("signature", None)
    payload = json.dumps(data, sort_keys=True).encode("utf-8")
    expected_sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not sig or not hmac.compare_digest(sig, expected_sig):
        print("[ERROR] Invalid mutation signature.", file=sys.stderr)
        sys.exit(1)
    return data

def cmd_run(mutation_path):
    verify_clean_checkout()
    mutation = verify_mutation(mutation_path)
    print(f"[RUNNER] Executing objective: {mutation['objective']}")
    cmd = mutation["allowed_commands"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)
    print("[TERMINAL] Execution complete.")

def cmd_dry_run(mutation_path):
    verify_clean_checkout()
    mutation = verify_mutation(mutation_path)
    print(f"[DRY-RUN] Validating objective: {mutation['objective']}")
    print("[DRY-RUN] Validation passed. Skipping physical command execution.")

def cmd_package():
    verify_clean_checkout()
    repo_root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip())
    genesis_dir = repo_root / "genesis"
    genesis_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
        "status": "packaged"
    }
    manifest_path = genesis_dir / "resurrection_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    
    bundle_path = genesis_dir / "resurrection_bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        tar.add(repo_root / "tools", arcname="tools")
    print(f"[PACKAGE] Bundle created at {bundle_path}")

def cmd_verify():
    get_secret()
    verify_clean_checkout()
    print("[VERIFIED] Boot verification passed successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cell_runner.py [verify|package|run|dry-run]")
        sys.exit(1)
    action = sys.argv[1]
    if action == "verify":
        cmd_verify()
    elif action == "package":
        cmd_package()
    elif action == "run":
        mutation_arg = sys.argv[sys.argv.index("--mutation") + 1] if "--mutation" in sys.argv else sys.exit(1)
        cmd_run(mutation_arg)
    elif action == "dry-run":
        mutation_arg = sys.argv[sys.argv.index("--mutation") + 1] if "--mutation" in sys.argv else sys.exit(1)
        cmd_dry_run(mutation_arg)
