#!/usr/bin/env python3
import os
import sys
import json
import hashlib
import hmac
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

LINEAGE_PATH = Path("memory/lineage.jsonl")
SECRET = os.environ.get("SOVEREIGN_CELL_SECRET", "sovereign_ephemeral_key_999").encode("utf-8")

def fail(msg: str, code: int = 1):
    print(f"[CRITICAL] {msg}", file=sys.stderr)
    sys.exit(code)

def run_git(args: list) -> str:
    res = subprocess.run(["git"] + args, capture_output=True, text=True)
    if res.returncode != 0:
        fail(f"Git command failed ('git {' '.join(args)}'): {res.stderr.strip()}")
    return res.stdout.strip()

def stage_1_verify():
    print("[RUNNER] Stage 1: Boot Verification...")
    
    # 1. Check Git repo root
    if not Path(".git").exists():
        fail("Current directory is not a Git repository checkout.")
        
    # 2. Check for uncommitted modifications to tracked files (ignoring untracked test files)
    res = subprocess.run(["git", "diff-index", "--quiet", "HEAD", "--"])
    if res.returncode != 0:
        fail("Working tree has uncommitted modifications to tracked files.")
        
    # 3. Verify lineage chain integrity
    if LINEAGE_PATH.exists():
        with open(LINEAGE_PATH, "r") as f:
            lines = f.readlines()
        expected_parent = hashlib.sha256(b"SOVEREIGN_GENESIS_ROOT_SEED").hexdigest()
        for idx, line in enumerate(lines):
            record = json.loads(line.strip())
            rec_hash = record.get("hash")
            data = record.get("data")
            calc_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
            if calc_hash != rec_hash:
                fail(f"Lineage tampering detected at block {idx}!")
            if idx > 0 and data.get("parent_lineage_hash") != expected_parent:
                fail(f"Lineage chain broken at block {idx}!")
            expected_parent = rec_hash
        print(f"[VERIFIED] Lineage chain intact ({len(lines)} blocks verified).")
    else:
        print("[WARNING] Lineage log not found; starting fresh root.")
        
    source_commit = run_git(["rev-parse", "HEAD"])
    print(f"[SUCCESS] Boot verification passed. Source Commit: {source_commit}")
    return source_commit

def stage_2_validate_mutation(mutation_path: str, source_commit: str) -> dict:
    print("[RUNNER] Stage 2: Mutation Validation...")
    m_path = Path(mutation_path)
    if not m_path.exists():
        fail(f"Mutation packet missing: {m_path}")
        
    with open(m_path, "r") as f:
        try:
            packet = json.load(f)
        except Exception as e:
            fail(f"Malformed JSON in mutation packet: {e}")
            
    required_fields = [
        "mutation_id", "parent_commit", "objective", "allowed_paths",
        "allowed_commands", "timeout_seconds", "memory_limit",
        "workload_seed", "output_schema", "submission_policy", "signature"
    ]
    for field in required_fields:
        if field not in packet:
            fail(f"Mutation packet missing required field: {field}")
            
    if packet["parent_commit"] != source_commit:
        fail(f"Parent commit mismatch! Expected {source_commit}, got {packet['parent_commit']}")
        
    # Verify signature
    sig_payload = {k: v for k, v in packet.items() if k != "signature"}
    payload_bytes = json.dumps(sig_payload, sort_keys=True).encode("utf-8")
    expected_sig = hmac.new(SECRET, payload_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, packet["signature"]):
        fail("Invalid mutation packet cryptographic signature!")
        
    print(f"[SUCCESS] Mutation packet {packet['mutation_id']} validated successfully.")
    return packet

def stage_3_execute(packet: dict, dry_run: bool):
    print(f"[RUNNER] Stage 3: Local Execution (Dry-Run: {dry_run})...")
    command = packet.get("allowed_commands")
    if not isinstance(command, list) or not command:
        fail("Allowed commands must be a non-empty list.")
        
    for path in packet.get("allowed_paths", []):
        if not Path(path).exists() and not Path(path).parent.exists():
            fail(f"Forbidden or non-existent path restriction violated: {path}")
            
    if dry_run:
        print("[DRY-RUN] Validation passed. Skipping command execution.")
        return {"exit_code": 0, "stdout": "", "stderr": "", "duration_s": 0.0}
        
    start_time = datetime.now(timezone.utc)
    try:
        res = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=packet.get("timeout_seconds", 60),
            check=False
        )
    except subprocess.TimeoutExpired:
        fail("Mutation execution exceeded timeout limit!")
    except Exception as e:
        fail(f"Execution fault: {e}")
        
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    print(f"[SUCCESS] Execution completed with exit code {res.returncode}")
    return {
        "exit_code": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "duration_s": duration
    }

def stage_4_evidence(packet: dict, exec_result: dict) -> dict:
    print("[RUNNER] Stage 4: Evidence Generation...")
    manifest = {
        "cell_id": "@ephemeral_cell_" + os.getenv("USER", "agent"),
        "mutation_id": packet["mutation_id"],
        "source_commit": packet["parent_commit"],
        "generation": 1,
        "execution_result": exec_result,
        "stdout_hash": hashlib.sha256(exec_result["stdout"].encode("utf-8")).hexdigest(),
        "stderr_hash": hashlib.sha256(exec_result["stderr"].encode("utf-8")).hexdigest(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    out_dir = Path("experiments/manifests")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"cell_evidence_{packet['mutation_id']}.json"
    
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"[SUCCESS] Evidence manifest sealed at {out_path}")
    return manifest

def stage_5_branch(packet: dict):
    print("[RUNNER] Stage 5: Branch Creation...")
    cell_id_sanitized = "@ephemeral_cell".replace("@", "").replace("/", "_")
    branch_name = f"cell/{cell_id_sanitized}/{packet['mutation_id']}"
    
    run_git(["checkout", "-b", branch_name])
    run_git(["add", "experiments/manifests/"])
    run_git(["commit", "-m", f"feat(cell): execute mutation {packet['mutation_id']}"])
    print(f"[SUCCESS] Created and committed to isolated branch: {branch_name}")
    return branch_name

def stage_6_submit(branch_name: str, authorized: bool):
    print(f"[RUNNER] Stage 6: Submission (Authorized: {authorized})...")
    if not authorized:
        print("[INFO] Submission mode is DRY_RUN/LOCAL. Stopping without network push.")
        return
        
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        fail("Authorized submission requested but GITHUB_TOKEN environment variable is absent.")
        
    run_git(["push", "origin", branch_name])
    print(f"[SUCCESS] Branch {branch_name} pushed to remote repository.")

def main():
    parser = argparse.ArgumentParser(description="Sovereign Seed Ephemeral Single-Shot Cell Runner")
    parser.add_argument("action", choices=["verify", "run", "package", "submit", "dry-run"])
    parser.add_argument("--mutation", type=str, help="Path to mutation JSON packet")
    parser.add_argument("--authorized", action="store_true", help="Enable authorized remote push")
    args = parser.parse_args()

    source_commit = stage_1_verify()
    
    if args.action == "verify":
        print("[TERMINATE] Verification check complete. Exiting.")
        sys.exit(0)
        
    if not args.mutation:
        fail("--mutation packet path required for this action.")
        
    packet = stage_2_validate_mutation(args.mutation, source_commit)
    
    if args.action == "dry-run":
        stage_3_execute(packet, dry_run=True)
        print("[TERMINATE] Dry run complete. Exiting.")
        sys.exit(0)
        
    exec_result = stage_3_execute(packet, dry_run=False)
    manifest = stage_4_evidence(packet, exec_result)
    branch_name = stage_5_branch(packet)
    
    is_auth = args.action == "submit" and args.authorized
    stage_6_submit(branch_name, is_auth)
    print("[TERMINATE] Cell execution lifecycle completed successfully. Terminating.")

if __name__ == "__main__":
    main()
