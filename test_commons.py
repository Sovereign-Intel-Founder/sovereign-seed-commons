import unittest
import urllib.request
import json
import threading
import time
from commons_bridge.bridge import SafeParticipantHandler, HOST, PORT
import http.server

class TestCommonsBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer((HOST, PORT), SafeParticipantHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_allowed_operation(self):
        url = f"http://{HOST}:{PORT}/"
        payload = json.dumps({"operation": "validate_cell"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["bound_address"], "127.0.0.1")

    def test_disallowed_operation(self):
        url = f"http://{HOST}:{PORT}/"
        payload = json.dumps({"operation": "arbitrary_shell_exec"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 403)

if __name__ == "__main__":
    unittest.main()
