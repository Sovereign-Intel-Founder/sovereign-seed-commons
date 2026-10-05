import sys
import os
import logging
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = os.getenv("COMMONS_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("COMMONS_BRIDGE_PORT", "8080"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("commons_bridge")

class SafeParticipantHandler(BaseHTTPRequestHandler):
    """Handles participant validation, message routing, and boundary checks."""

    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception:
            self.send_error(400, "Invalid JSON")
            return

        op = payload.get("operation")
        if op == "validate_cell":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "success", "bound_address": "127.0.0.1"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(403, "Disallowed operation")

    def validate_participant(self, participant_id: str) -> bool:
        if not participant_id or not isinstance(participant_id, str):
            return False
        return True

    def process_message(self, payload: dict) -> bool:
        if not isinstance(payload, dict):
            return False
        logger.info(f"Processing bridge payload type: {payload.get('type', 'unknown')}")
        return True

def main():
    logger.info(f"Sovereign Seed Commons Bridge Active on {HOST}:{PORT}")
    server = HTTPServer((HOST, PORT), SafeParticipantHandler)
    print("Bridge initialized successfully.")
    server.serve_forever()

if __name__ == "__main__":
    main()
