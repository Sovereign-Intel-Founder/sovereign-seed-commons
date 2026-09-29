import http.server
import threading
import urllib.request
import json
import sys
import os

# Guarantee root directory module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from safe_participant_handler import SafeParticipantHandler

HOST = "127.0.0.1"
PORT = 8080

class ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

def run_integration_test():
    print("[INTEGRATION] Starting Sovereign Seed Commons standalone HTTP test...")
    server = ReusableHTTPServer((HOST, PORT), SafeParticipantHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # 1. Test POST operation (ping)
        req = urllib.request.Request(
            f"http://{HOST}:{PORT}",
            data=json.dumps({"operation": "ping"}).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res_data = json.loads(resp.read().decode('utf-8'))
            assert res_data.get("status") == "success"
            print("  ✅ POST / ping operation verified")

        # 2. Test GET operation (status)
        with urllib.request.urlopen(f"http://{HOST}:{PORT}") as resp:
            assert resp.status == 200
            res_data = json.loads(resp.read().decode('utf-8'))
            assert res_data.get("status") == "active"
            print("  ✅ GET / status healthcheck verified")

        print("[SUCCESS] Standalone integration test completed with zero errors.")

    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    run_integration_test()
