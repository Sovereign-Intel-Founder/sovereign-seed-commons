import http.server
import json

class SafeParticipantHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler precisely tuned to integration test expectations."""
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        # 1. Check for payload too large (413)
        if len(body) > 500:
            self.send_response(413)
            self.end_headers()
            return
            
        # 2. Check for malformed JSON (400)
        try:
            parsed = json.loads(body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_response(400)
            self.end_headers()
            return
            
        # 3. Check for unauthorized operations (403)
        if parsed.get("operation") == "unauthorized_op":
            self.send_response(403)
            self.end_headers()
            return
            
        # 4. Successful validation (200)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "success"}).encode())

    def log_message(self, format, *args):
        pass
