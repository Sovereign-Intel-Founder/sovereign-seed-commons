import os
import subprocess
import re

def inspect_system():
    print("=== 1. ACTIVE LISTENING PORTS ===")
    try:
        res = subprocess.run(["ss", "-tln"], capture_output=True, text=True, timeout=3)
        print(res.stdout if res.stdout else "No output from ss.")
    except Exception as e:
        print(f"Could not run ss command: {e}")

    print("\n=== 2. SCANNING ENTRY POINTS & PORT BINDINGS ===")
    target_keywords = ["bootstrap", "gossip", "daemon", "bridge", "rpc", "master"]
    
    for root, dirs, files in os.walk("."):
        if any(ex in root for ex in [".git", "evidence", "build", "__pycache__"]):
            continue
        for f in files:
            if f.endswith((".py", ".c", ".sh", ".json")):
                if any(kw in f.lower() for kw in target_keywords):
                    path = os.path.join(root, f)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as file:
                            content = file.read()
                            # Look for port assignments or server bindings
                            ports = re.findall(r'(?:port|PORT|bind|LISTEN|listen)[^\d]*(\d{2,5})', content)
                            if ports or "def main" in content or "if __name__" in content:
                                unique_ports = list(set(ports))
                                print(f"File: {path}")
                                if unique_ports:
                                    print(f"  -> Detected Port References: {unique_ports}")
                    except Exception:
                        pass

if __name__ == "__main__":
    inspect_system()
