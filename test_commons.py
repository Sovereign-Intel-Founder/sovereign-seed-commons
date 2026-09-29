import unittest
import http.server
import threading
import urllib.request
import json
from safe_participant_handler import SafeParticipantHandler

HOST = "127.0.0.1"
PORT = 8080  # Dedicated Sovereign Toll Bridge Port

class ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

class TestCommonsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ReusableHTTPServer((HOST, PORT), SafeParticipantHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_allowed_operation(self):
        req = urllib.request.Request(
            f"http://{HOST}:{PORT}",
            data=json.dumps({"operation": "ping"}).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)

    def test_disallowed_operation(self):
        req = urllib.request.Request(
            f"http://{HOST}:{PORT}",
            data=json.dumps({"operation": "unauthorized_command"}).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

if __name__ == "__main__":
    unittest.main()
