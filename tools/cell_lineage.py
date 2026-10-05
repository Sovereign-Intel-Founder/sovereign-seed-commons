import os
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone

LINEAGE_PATH = Path("memory/lineage.jsonl")

def compute_string_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def record_mutation(cell_id: str, parent_hash: str, mutation_description: str):
    print(f"[LINEAGE] Recording generational mutation for {cell_id}...")
    
    LINEAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    mutation_payload = {
        "cell_id": cell_id,
        "parent_lineage_hash": parent_hash,
        "mutation_description": mutation_description,
        "timestamp": timestamp,
        "protocol": "Sovereign Seed Commons"
    }
    
    payload_str = json.dumps(mutation_payload, sort_keys=True)
    current_hash = compute_string_sha256(payload_str)
    
    record = {
        "hash": current_hash,
        "data": mutation_payload
    }
    
    # Append-only immutable lineage log (JSONL)
    with open(LINEAGE_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
        
    print(f"[SUCCESS] Lineage record appended. Cell Hash: {current_hash[:16]}... (Parent: {parent_hash[:16]}...)")
    return current_hash

if __name__ == "__main__":
    # Example: Simulating Genesis -> Alpha -> Gamma mutation lineage
    genesis_hash = compute_string_sha256("SOVEREIGN_GENESIS_ROOT_SEED")
    
    alpha_hash = record_mutation(
        cell_id="@research_cell_alpha",
        parent_hash=genesis_hash,
        mutation_description="Initial base cell synchronization and secure IPC socket integration."
    )
    
    gamma_hash = record_mutation(
        cell_id="@research_cell_gamma",
        parent_hash=alpha_hash,
        mutation_description="Applied microsecond latency optimization via lock-free queue buffering."
    )
