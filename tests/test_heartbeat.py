import unittest
import os
import sys
import shutil

sys.path.insert(0, os.path.abspath("."))
from commons_bridge.bootstrap import bootstrap_node, STATE_DIR
from commons_bridge.enrollment import create_enrollment_request
from commons_bridge.heartbeat import send_heartbeat, load_hb_state

SIP_DIR = os.path.expanduser("~/sovereign_workspace/sovereign-intelligence")
if not os.path.exists(SIP_DIR):
    SIP_DIR = os.path.expanduser("~/sovereignintelfounder")
sys.path.insert(0, SIP_DIR)
from core.node_control_plane import TollBridgeLedger

class TestHeartbeat(unittest.TestCase):
    def setUp(self):
        if os.path.exists(STATE_DIR):
            shutil.rmtree(STATE_DIR)
        self.identity = bootstrap_node()
        self.ledger = TollBridgeLedger()
        payload, sig = create_enrollment_request(self.identity)
        self.ledger.process_enrollment(payload, sig)

    def tearDown(self):
        if os.path.exists(STATE_DIR):
            shutil.rmtree(STATE_DIR)

    def test_successful_heartbeat(self):
        res = send_heartbeat(ledger_client=self.ledger)
        self.assertEqual(res["status"], "ACK")
        self.assertEqual(res["sequence"], 1)

    def test_sequence_increment(self):
        send_heartbeat(ledger_client=self.ledger)
        res2 = send_heartbeat(ledger_client=self.ledger)
        self.assertEqual(res2["status"], "ACK")
        self.assertEqual(res2["sequence"], 2)

        st = load_hb_state()
        self.assertEqual(st["sequence"], 2)

if __name__ == "__main__":
    unittest.main()
