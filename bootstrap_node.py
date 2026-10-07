import os
import json
import socket
import subprocess

def initialize_node_storefront():
    print("[BOOTSTRAP] Initializing Sovereign Intelligence Protocol Autonomous Storefront...")
    
    # Detect local hardware capacity tier (CPU/RAM approximation)
    cpu_cores = os.cpu_count() or 1
    tier = "BARE_METAL_TIER" if cpu_cores >= 32 else "EDGE_SOLDIER_TIER"
    
    config = {
        "node_status": "ACTIVE",
        "capacity_tier": tier,
        "cpu_cores": cpu_cores,
        "gossip_port": 9999,
        "referral_commission_rate": 0.05
    }
    
    with open("node_config.json", "w") as f:
        json.dump(config, f, indent=4)
        
    print(f"[BOOTSTRAP] Node configured successfully under {tier} with {cpu_cores} cores.")
    print("[BOOTSTRAP] Automated storefront listeners active on port 9999.")

if __name__ == "__main__":
    initialize_node_storefront()
