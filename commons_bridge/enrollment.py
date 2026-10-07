import os
import json
import time
import uuid
import hashlib
import hmac
from commons_bridge.bootstrap import STATE_DIR, IDENTITY_FILE, bootstrap_node

RECEIPT_FILE = os.path.join(STATE_DIR, "enrollment_receipt.json")

def sign_payload(secret_key: str, payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), serialized, hashlib.sha256).hexdigest()

def create_enrollment_request(identity: dict) -> tuple:
    payload = {
        "node_id": identity["node_id"],
        "public_key": identity["public_key"],
        "protocol_version": identity["protocol_version"],
        "software_version": identity["software_version"],
        "timestamp": time.time(),
        "nonce": uuid.uuid4().hex
    }
    signature = sign_payload(identity["secret_key"], payload)
    return payload, signature

def persist_receipt(receipt_data: dict):
    with open(RECEIPT_FILE, "w") as f:
        json.dump(receipt_data, f, indent=2)

def load_receipt():
    if os.path.exists(RECEIPT_FILE):
        with open(RECEIPT_FILE, "r") as f:
            return json.load(f)
    return None

def enroll_node(ledger_client=None):
    identity = bootstrap_node()
    existing_receipt = load_receipt()
    if existing_receipt:
        print(f"[ENROLLMENT] Loaded existing receipt: {existing_receipt.get('receipt_id')}")
        return existing_receipt

    payload, signature = create_enrollment_request(identity)
    if ledger_client:
        response = ledger_client.process_enrollment(payload, signature)
    else:
        import sys
        sip_dir = os.path.expanduser("~/sovereign_workspace/sovereign-intelligence")
        if not os.path.exists(sip_dir):
            sip_dir = os.path.expanduser("~/sovereignintelfounder")
        sys.path.append(sip_dir)
        from core.node_control_plane import TollBridgeLedger
        ledger = TollBridgeLedger()
        response = ledger.process_enrollment(payload, signature)

    if response.get("status") == "SUCCESS":
        persist_receipt(response)
        print(f"[ENROLLMENT] Enrollment successful. Receipt: {response.get('receipt_id')}")
        return response
    else:
        raise RuntimeError(f"Enrollment failed: {response.get('reason')}")
