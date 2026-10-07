import socket
import time
import subprocess

TARGET_IP = "127.0.0.1"  # Points back to master core or command node
PORT = 9999

def enlist_and_serve():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("[SOLDIER] Automated agent initialized. Enlisting in Sovereign Mesh...")
    
    while True:
        try:
            # Send automated traffic and heartbeat to master
            payload = b"SIP_AUTOMATED_SOLDIER_HEARTBEAT_READY"
            sock.sendto(payload, (TARGET_IP, PORT))
            
            # Simulate automated workload execution
            time.sleep(10)
        except Exception as e:
            print(f"[SOLDIER] Connection retry error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    enlist_and_serve()
