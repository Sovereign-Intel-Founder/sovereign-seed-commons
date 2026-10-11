import os
import json
import urllib.request
import urllib.error

def check_rpc():
    print("=== RPC WIRING & CONNECTIVITY DIAGNOSTIC ===")
    
    # Check common environment variables or default to local validator/RPC port
    rpc_url = os.getenv("SOLANA_RPC_URL", os.getenv("RPC_ENDPOINT", "http://127.0.0.1:8899"))
    print(f"Target RPC Endpoint: {rpc_url}")
    
    try:
        req = urllib.request.Request(
            rpc_url,
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getHealth"}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=3.0) as response:
            result = json.loads(response.read().decode())
            print(f"RPC Connection Status: SUCCESS")
            print(f"Node Health Response: {result}")
    except urllib.error.URLError as e:
        print(f"RPC Connection Status: FAILED/UNREACHABLE ({e.reason})")
        print("Note: If your node runs on a custom port, UNIX socket, or requires specific headers/auth, verify your local configuration.")
    except Exception as e:
        print(f"RPC Connection Status: ERROR ({e})")

if __name__ == "__main__":
    check_rpc()
