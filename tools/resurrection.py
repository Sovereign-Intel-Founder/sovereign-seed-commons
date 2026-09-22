import os
import json
import tarfile
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone

BUNDLE_PATH = "genesis/resurrection_bundle.tar.gz"
MANIFEST_PATH = "genesis/resurrection_manifest.json"

def compute_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def export_state():
    print("[MIGRATE] Initializing sovereign state export...")
    
    required_paths = [
        Path("governance/voting_ledger.json"),
        Path("SOVEREIGN_SEED_MASTER_EXECUTION_PLAN.md"),
        Path("constitution.md") if Path("constitution.md").exists() else Path("CONSTITUTION.md")
    ]
    
    Path("genesis").mkdir(parents=True, exist_ok=True)
    with tarfile.open(BUNDLE_PATH, "w:gz") as tar:
        for path in required_paths:
            if path.exists():
                tar.add(path)
                print(f"[MIGRATE] Added to bundle: {path}")
        
        memory_dir = Path("memory")
        if memory_dir.exists():
            tar.add(memory_dir)
            print(f"[MIGRATE] Added memory lineage: {memory_dir}")

    bundle_hash = compute_sha256(Path(BUNDLE_PATH))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    manifest = {
        "protocol": "Sovereign Seed Commons",
        "phase": "P11 Migration and Resurrection",
        "bundle_sha256": bundle_hash,
        "timestamp": timestamp
    }
    
    with open(MANIFEST_PATH, "w") as mf:
        json.dump(manifest, mf, indent=2)
        
    print(f"[SUCCESS] Resurrection bundle sealed at {BUNDLE_PATH}")
    print(f"[SUCCESS] Cryptographic manifest written to {MANIFEST_PATH} (SHA-256: {bundle_hash})")

def verify_and_resurrect(target_dir: str):
    print(f"[RESURRECT] Inspecting resurrection package for deployment at {target_dir}...")
    if not Path(BUNDLE_PATH).exists() or not Path(MANIFEST_PATH).exists():
        print("[CRITICAL] Resurrection bundle or manifest missing.", file=sys.stderr)
        sys.exit(1)
        
    current_hash = compute_sha256(Path(BUNDLE_PATH))
    with open(MANIFEST_PATH, "r") as mf:
        manifest = json.load(mf)
        
    if current_hash != manifest.get("bundle_sha256"):
        print("[SECURITY ALERT] Bundle checksum mismatch! State integrity compromised.", file=sys.stderr)
        sys.exit(1)
        
    print("[VERIFIED] Checksum matches manifest. Extracting sovereign state securely...")
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)
    
    with tarfile.open(BUNDLE_PATH, "r:gz") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo():
                raise RuntimeError(f"[SECURITY ALERT] Unsafe file type detected in archive: {member.name}")
                
            member_path = (target_path / member.name).resolve()
            if not member_path.is_relative_to(target_path):
                raise RuntimeError(f"[SECURITY ALERT] Path traversal detected: {member.name}")
                
        tar.extractall(path=target_path)
        
    print(f"[SUCCESS] Sovereign state successfully resurrected into {target_path}.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "resurrect":
        target = sys.argv[2] if len(sys.argv) > 2 else "."
        verify_and_resurrect(target)
    else:
        export_state()
