import os
import json
import time
import uuid
from commons_bridge.bootstrap import STATE_DIR, bootstrap_node
from commons_bridge.enrollment import sign_payload

HB_STATE_FILE = os.path.join(STATE_DIR, "heartbeat_state.json")

def load_hb_state():
    if os.path.exists(HB_STATE_FILE):
        with open(HB_STATE_FILE, "r") as f:
            return json.load(f)
    return {"sequence": 0, "last_timestamp": 0}

def save_hb_state(seq, timestamp):
    with open(HB_STATE_FILE, "w") as f:
        json.dump({"sequence": seq, "last_timestamp": timestamp}, f, indent=2)

def send_heartbeat(ledger_client=None):
    identity = bootstrap_node()
    hb_state = load_hb_state()
    new_seq = hb_state["sequence"] + 1
    now = time.time()

    payload = {
        "node_id": identity["node_id"],
        "sequence": new_seq,
        "timestamp": now,
        "nonce": uuid.uuid4().hex
    }
    sig = sign_payload(identity["secret_key"], payload)

    if ledger_client:
        res = ledger_client.process_heartbeat(payload, sig)
    else:
        import sys
        sip_dir = os.path.expanduser("~/sovereign_workspace/sovereign-intelligence")
        if not os.path.exists(sip_dir):
            sip_dir = os.path.expanduser("~/sovereignintelfounder")
        sys.path.append(sip_dir)
        from core.node_control_plane import TollBridgeLedger
        ledger = TollBridgeLedger()
        res = ledger.process_heartbeat(payload, sig)

    if res.get("status") == "ACK":
        save_hb_state(new_seq, now)
        print(f"[HEARTBEAT] Seq {new_seq} acknowledged.")
        return res
    else:
        raise RuntimeError(f"Heartbeat rejected: {res}")
