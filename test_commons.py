import unittest
import http.server
import threading
import urllib.request
import json
import os
from safe_participant_handler import SafeParticipantHandler

HOST = "127.0.0.1"
PORT = int(os.environ.get("COMMONS_BRIDGE_PORT", 8081))

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
