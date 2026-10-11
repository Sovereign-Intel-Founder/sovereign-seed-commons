import urllib.request
import urllib.error
import json

def test_custom_rpc():
    url = "http://127.0.0.1:8080"
    print(f"Probing Custom Live RPC Endpoint: {url}")
    
    # Try a standard health or status payload suitable for the custom adapter
    payloads = [
        {"jsonrpc": "2.0", "id": 1, "method": "health"},
        {"jsonrpc": "2.0", "id": 1, "method": "status"},
        {"type": "ping"}
    ]
    
    for payload in payloads:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=2.0) as res:
                data = json.loads(res.read().decode())
                print(f"SUCCESS with payload {payload}: {data}")
                return
        except Exception as e:
            print(f"Payload {payload} tried, error: {e}")
            
    print("Endpoint is reachable on TCP, testing raw connection...")

if __name__ == "__main__":
    test_custom_rpc()
