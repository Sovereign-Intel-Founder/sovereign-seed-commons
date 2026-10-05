import http.server
import json
import logging

logging.basicConfig(level=logging.INFO)

class SafeParticipantHandler(http.server.BaseHTTPRequestHandler):
    """
    Offline-by-default, local-only participant cell request handler.
    Inherits from BaseHTTPRequestHandler to integrate seamlessly with HTTPServer.
    """
    ALLOWED_OPERATIONS = {"ping", "validate_state", "echo_evidence", "get_status"}

    def do_GET(self):
        self._send_json({"status": "active", "cell": "sovereign-seed-participant"}, status_code=200)

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode('utf-8')) if body else {}

            operation = payload.get("operation")
            if operation not in self.ALLOWED_OPERATIONS:
                self._send_json({"error": f"Disallowed or unknown operation: {operation}"}, status_code=400)
                return

            # Handle safe local operations
            response = {
                "status": "success",
                "operation": operation,
                "result": "processed_offline_cell"
            }
            self._send_json(response, status_code=200)

        except Exception as e:
            self._send_json({"error": str(e)}, status_code=500)

    def _send_json(self, data, status_code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress standard http server stderr log spam during tests
        pass
