import http.server
import json

class SafeParticipantHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for safe participant integration testing."""
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        # Match integration test expectations
        if len(body) > 500 or b"large_body" in body:
            self.send_response(413)
            self.end_headers()
            return
            
        if b"not-valid-json" in body:
            self.send_response(400)
            self.end_headers()
            return
            
        auth = self.headers.get('Authorization', '')
        if not auth or 'secret' not in auth:
            self.send_response(401)
            self.end_headers()
            return
            
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "success"}).encode())

    def log_message(self, format, *args):
        # Suppress logging noise during tests
        pass
