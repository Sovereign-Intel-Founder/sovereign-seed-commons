import os
import sys

def enforce_sandbox():
    """
    Enforces strict workload isolation. Fails closed if the execution 
    environment is not containerized or sandboxed.
    """
    is_containerized = os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")
    
    # Enforce strict isolation unless an explicit local debug override is set
    if not is_containerized and os.getenv("SIP_ALLOW_UNSANDBOXED", "false").lower() != "true":
        print("[SECURITY ERROR] Cell execution aborted: Unsandboxed environment detected.")
        print("[SECURITY ERROR] Tasks must run within a locked-down container or microVM.")
        sys.exit(1)
        
    print("[SECURITY OK] Sandbox isolation verified.")

if __name__ == "__main__":
    enforce_sandbox()
