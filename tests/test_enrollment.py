import unittest
import os
import time
import uuid
import sys
import shutil

sys.path.insert(0, os.path.abspath("."))
from commons_bridge.bootstrap import bootstrap_node, STATE_DIR
from commons_bridge.enrollment import create_enrollment_request, enroll_node, RECEIPT_FILE

SIP_DIR = os.path.expanduser("~/sovereign_workspace/sovereign-intelligence")
if not os.path.exists(SIP_DIR):
    SIP_DIR = os.path.expanduser("~/sovereignintelfounder")
sys.path.insert(0, SIP_DIR)
from core.node_control_plane import TollBridgeLedger

class TestEnrollment(unittest.TestCase):
    def setUp(self):
        if os.path.exists(STATE_DIR):
            shutil.rmtree(STATE_DIR)
        self.identity = bootstrap_node()
        self.ledger = TollBridgeLedger()

    def tearDown(self):
        if os.path.exists(STATE_DIR):
            shutil.rmtree(STATE_DIR)

    def test_valid_enrollment(self):
        payload, signature = create_enrollment_request(self.identity)
        res = self.ledger.process_enrollment(payload, signature)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("receipt_id", res)

    def test_stale_timestamp(self):
        payload, signature = create_enrollment_request(self.identity)
        payload["timestamp"] = time.time() - 400
        res = self.ledger.process_enrollment(payload, signature)
        self.assertEqual(res["status"], "REJECTED")

    def test_replayed_nonce(self):
        payload, signature = create_enrollment_request(self.identity)
        res1 = self.ledger.process_enrollment(payload, signature)
        res2 = self.ledger.process_enrollment(payload, signature)
        self.assertEqual(res2["status"], "REJECTED")

    def test_restart_persistence(self):
        res = enroll_node(ledger_client=self.ledger)
        self.assertTrue(os.path.exists(RECEIPT_FILE))
        res2 = enroll_node(ledger_client=self.ledger)
        self.assertEqual(res["receipt_id"], res2["receipt_id"])

if __name__ == "__main__":
    unittest.main()
