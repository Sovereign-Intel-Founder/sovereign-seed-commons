import os
import json
from cryptography.fernet import Fernet

def generate_task_key():
    """Generates an ephemeral encryption key for a task payload."""
    return Fernet.generate_key().decode()

def encrypt_payload(data: dict, key: str) -> str:
    """Encrypts task data so it remains completely opaque in transit."""
    f = Fernet(key.encode())
    serialized = json.dumps(data).encode()
    return f.encrypt(serialized).decode()

def decrypt_payload(token: str, key: str) -> dict:
    """Decrypts task data strictly inside the authorized, sandboxed cell."""
    f = Fernet(key.encode())
    decrypted = f.decrypt(token.encode())
    return json.loads(decrypted.decode())

if __name__ == "__main__":
    # Test internal protocol security wrap
    test_key = generate_task_key()
    sample_data = {"objective": "process_confidential_state", "payload_hash": "sha256:abc123xyz"}
    
    encrypted = encrypt_payload(sample_data, test_key)
    print(f"[CRYPTO OK] Payload successfully encrypted for transit: {encrypted[:30]}...")
    
    recovered = decrypt_payload(encrypted, test_key)
    print(f"[CRYPTO OK] Payload safely decrypted inside sandbox: {recovered['objective']}")
