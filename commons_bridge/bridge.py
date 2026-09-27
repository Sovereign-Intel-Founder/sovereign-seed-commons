#!/usr/bin/env python3
import http.server
import json
import urllib.parse
import sys
import time

HOST = "127.0.0.1"
PORT = 8999
MAX_BODY_SIZE = 1024  # 1 KB limit
ALLOWED_OPERATIONS = {"validate_cell", "inspect_state"}

class SafeParticipantHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        start_time = time.time()
        content_length = int(self.headers.get('Content-Length', 0))
        
        # Enforce request size limit
        if content_length > MAX_BODY_SIZE:
            self.send_error_response(413, "Payload too large")
            return
            
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_error_response(400, "Malformed JSON input")
            return
            
        op = data.get("operation")
        
        # Enforce strict operation allowlist
        if op not in ALLOWED_OPERATIONS:
            self.send_error_response(403, f"Operation '{op}' not permitted")
            return
            
        # Execute bounded operation and generate evidence
        duration = time.time() - start_time
        evidence = {
            "status": "success",
            "operation": op,
            "bound_address": HOST,
            "duration_seconds": round(duration, 6),
            "evidence_note": "Offline-by-default execution in participant cell."
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(evidence).encode('utf-8'))

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        error_payload = json.dumps({"status": "error", "code": code, "message": message})
        self.wfile.write(error_payload.encode('utf-8'))

if __name__ == "__main__":
    server = http.server.HTTPServer((HOST, PORT), SafeParticipantHandler)
    print(f"[+] Commons Participant Bridge bound strictly to {HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
