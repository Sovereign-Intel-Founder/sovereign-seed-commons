import json, hmac, hashlib, subprocess
from pathlib import Path

repo_root = Path(".")
net_dir = repo_root / "experiments/p12_network"
net_dir.mkdir(parents=True, exist_ok=True)

source_commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
secret = b"sovereign_ephemeral_key_999"

# Cell A Packet
packet_a = {
    "mutation_id": "mut-p12-cell-alpha",
    "parent_commit": source_commit,
    "objective": "P12 Multi-Cell Network Execution - Cell Alpha",
    "allowed_paths": ["tools/"],
    "allowed_commands": ["python3", "-c", "print('CELL_ALPHA_SUCCESS')"],
    "timeout_seconds": 5,
    "submission_policy": "local_only"
}
payload_a = {k: v for k, v in packet_a.items() if k != "signature"}
packet_a["signature"] = hmac.new(secret, json.dumps(payload_a, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
(net_dir / "p12_cell_a.json").write_text(json.dumps(packet_a, indent=2))

# Cell B Packet
packet_b = {
    "mutation_id": "mut-p12-cell-bravo",
    "parent_commit": source_commit,
    "objective": "P12 Multi-Cell Network Execution - Cell Bravo",
    "allowed_paths": ["tools/"],
    "allowed_commands": ["python3", "-c", "print('CELL_BRAVO_SUCCESS')"],
    "timeout_seconds": 5,
    "submission_policy": "local_only"
}
payload_b = {k: v for k, v in packet_b.items() if k != "signature"}
packet_b["signature"] = hmac.new(secret, json.dumps(payload_b, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
(net_dir / "p12_cell_b.json").write_text(json.dumps(packet_b, indent=2))

print("[P12] Created cell alpha and bravo mutation packets successfully.")
