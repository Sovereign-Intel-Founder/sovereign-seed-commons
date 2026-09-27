import sys
import os
import threading
import http.client
import json
import unittest
import http.server
import socketserver

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from commons_bridge.bridge import SafeParticipantHandler

class TestSafeParticipantIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), SafeParticipantHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)

    def _make_request(self, method, body=None, headers=None):
        if headers is None:
            headers = {"Content-Type": "application/json"}
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, "/", body=body, headers=headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, data

    def test_a_validate_cell_success(self):
        payload = json.dumps({"operation": "validate_cell"})
        status, data = self._make_request("POST", body=payload)
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertEqual(parsed.get("status"), "success")

    def test_b_unauthorized_operation(self):
        payload = json.dumps({"operation": "unauthorized_op"})
        status, data = self._make_request("POST", body=payload)
        self.assertEqual(status, 403)

    def test_c_malformed_json(self):
        status, data = self._make_request("POST", body="not-valid-json")
        self.assertEqual(status, 400)

    def test_d_payload_too_large(self):
        large_body = json.dumps({"operation": "validate_cell", "padding": "x" * 1200})
        status, data = self._make_request("POST", body=large_body)
        self.assertEqual(status, 413)

if __name__ == "__main__":
    unittest.main()
