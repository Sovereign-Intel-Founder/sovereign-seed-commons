import os
import sys
import asyncio
import sqlite3
import tempfile
import threading
from pathlib import Path

# Resolve system paths cleanly
sys.path.append(str(Path("tollbridge_system/src").resolve()))

import nacl.signing
from solders.keypair import Keypair
from tollbridge.security import verify_production_safety, verify_ed25519_envelope
from tollbridge.ingress_metering import IngressMeteringEngine


def test_cryptographic_fuzzing_and_fault_injection():
    print("\n[STRESS TEST 1] Cryptographic Fault Injection & Fuzzing...")

    # Generate baseline keypair
    kp = Keypair()
    pubkey_str = str(kp.pubkey())
    message = b"sovereign-payload-v1:telemetry-packet-9921"
    
    # Sign payload using solders API (sign_message -> bytes -> hex)
    signature = kp.sign_message(message)
    signature_bytes = bytes(signature)
    signature_hex = signature_bytes.hex()

    # 1. Baseline Valid Signature
    assert verify_ed25519_envelope(pubkey_str, message, signature_hex) == True, "Valid signature failed verification!"
    print("  -> PASSED: Valid Ed25519 signature verified.")

    # 2. Truncated Signature
    assert verify_ed25519_envelope(pubkey_str, message, signature_hex[:-4]) == False, "Truncated signature accepted!"
    print("  -> PASSED: Truncated signature rejected.")

    # 3. Bit-Flip Mutation
    mutated_bytes = bytearray(bytes.fromhex(signature_hex))
    mutated_bytes[0] ^= 0xFF
    assert verify_ed25519_envelope(pubkey_str, message, mutated_bytes.hex()) == False, "Bit-flipped signature accepted!"
    print("  -> PASSED: Bit-flipped signature rejected.")

    # 4. Garbage Hex Data
    assert verify_ed25519_envelope(pubkey_str, message, "deadbeef" * 8) == False, "Garbage hex accepted!"
    print("  -> PASSED: Malformed garbage hex rejected.")

    # 5. Key Mismatch Injection
    wrong_kp = Keypair()
    assert verify_ed25519_envelope(str(wrong_kp.pubkey()), message, signature_hex) == False, "Key mismatch accepted!"
    print("  -> PASSED: Key mismatch correctly rejected.")


def test_safety_boundary_matrix():
    print("\n[STRESS TEST 2] Environmental Safety Boundary Matrix...")

    os.environ["SIP_MAINNET_LIVE"] = "0"
    assert verify_production_safety() == False, "Failed to block execution when flag is 0!"

    os.environ["SIP_MAINNET_LIVE"] = "true"  # Invalid format, strictly requires "1"
    assert verify_production_safety() == False, "Failed to block execution on invalid string format!"

    os.environ["SIP_MAINNET_LIVE"] = "1"
    assert verify_production_safety() == True, "Failed to activate mainnet mode when flag is 1!"
    print("  -> PASSED: Strict mainnet safety gates enforced.")


def test_sqlite_wal_concurrency_stress():
    print("\n[STRESS TEST 3] SQLite WAL Concurrency Stress...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "stress_vault.db"

        # Initialize WAL mode database
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_stress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pubkey TEXT,
                bytes_processed INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        def worker_write(worker_id):
            c = sqlite3.connect(db_path, timeout=30.0)
            for i in range(500):
                c.execute(
                    "INSERT INTO telemetry_stress (pubkey, bytes_processed) VALUES (?, ?)",
                    (f"pubkey_{worker_id}", i * 10)
                )
            c.commit()
            c.close()

        # Launch 10 concurrent threads hammering the WAL engine
        threads = [threading.Thread(target=worker_write, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Audit total inserted records
        verify_conn = sqlite3.connect(db_path)
        count = verify_conn.execute("SELECT COUNT(*) FROM telemetry_stress").fetchone()[0]
        verify_conn.close()

        assert count == 5000, f"Expected 5000 records under WAL stress, found {count}!"
        print(f"  -> PASSED: Processed {count} concurrent writes cleanly with zero deadlocks or corruption.")


if __name__ == "__main__":
    print("=== INITIALIZING ADVANCED RIGOR & STRESS SUITE ===")
    test_cryptographic_fuzzing_and_fault_injection()
    test_safety_boundary_matrix()
    test_sqlite_wal_concurrency_stress()
    print("\n=== ALL RIGOR & STRESS TESTS PASSED PERFECTLY ===")
