import os
import json
import uuid
import hashlib
import sys

STATE_DIR = os.path.expanduser("~/.sip_node_state")
IDENTITY_FILE = os.path.join(STATE_DIR, "commons_identity.json")

def bootstrap_node(bootstrap_url=None, tier="edge_node"):
    os.makedirs(STATE_DIR, exist_ok=True)
    
    if os.path.exists(IDENTITY_FILE):
        with open(IDENTITY_FILE, "r") as f:
            identity = json.load(f)
        print(f"[BOOTSTRAP] Existing identity loaded: {identity['node_id']}")
        return identity

    secret_key = os.urandom(32).hex()
    public_key = hashlib.sha256(secret_key.encode("utf-8")).hexdigest()
    node_id = f"commons-node-{uuid.uuid4().hex[:12]}"
    
    # Default SIP Toll Bridge endpoint on port 8000 to prevent localhost collisions
    url = bootstrap_url or os.getenv("SIP_BOOTSTRAP_URL", "http://127.0.0.1:8000")

    identity = {
        "node_id": node_id,
        "secret_key": secret_key,
        "public_key": public_key,
        "protocol_version": "1.0.0",
        "software_version": "2.0.0",
        "tier": tier,
        "bootstrap_url": url,
        "created_at": os.path.getmtime(STATE_DIR) if os.path.exists(STATE_DIR) else 0
    }

    with open(IDENTITY_FILE, "w") as f:
        json.dump(identity, f, indent=2)

    print(f"[BOOTSTRAP] Created new durable node identity: {node_id}")
    return identity

if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else None
    ident = bootstrap_node(bootstrap_url=url_arg)
    print(f"Node ID:     {ident['node_id']}")
    print(f"Public Key:  {ident['public_key']}")
    print(f"Target URL:  {ident['bootstrap_url']}")
