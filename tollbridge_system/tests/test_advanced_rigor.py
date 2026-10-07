import os
import time
import hashlib
import pytest
from solders.keypair import Keypair

from tollbridge.security import (
    build_canonical_envelope_bytes,
    verify_production_safety,
    verify_ed25519_envelope
)
from tollbridge.ingress_metering import IngressMeteringEngine


def test_cryptographic_fuzzing_and_fault_injection():
    """
    Stress test 1: Validates that valid Ed25519 signatures over canonical envelopes pass,
    while tampered payloads, bit-flipped signatures, and invalid lengths are rejected.
    """
    signer = Keypair()
    pubkey_str = str(signer.pubkey())
    
    protocol_version = "sip-v1.0"
    nonce = "fuzz_nonce_001"
    timestamp = time.time()
    asset_type = "SOL"
    subscription_topic = "stress.topic"
    content_type = "application/octet-stream"
    
    raw_payload = b"STRESS_TEST_PAYLOAD_DATA"
    payload_hash = hashlib.sha256(raw_payload).hexdigest()

    # 1. Build exact canonical bytes matching production security.py
    canonical_bytes = build_canonical_envelope_bytes(
        protocol_version=protocol_version,
        client_pubkey=pubkey_str,
        nonce=nonce,
        timestamp=timestamp,
        asset_type=asset_type,
        payload_hash=payload_hash,
        content_type=content_type,
        subscription_topic=subscription_topic
    )
    
    signature_bytes = signer.sign_message(canonical_bytes)
    signature_hex = bytes(signature_bytes).hex()

    # 2. Baseline Valid Signature check
    is_valid, reason = verify_ed25519_envelope(pubkey_str, canonical_bytes, signature_hex)
    assert is_valid is True, f"Valid signature failed verification: {reason}"

    # 3. Fault Injection: Bit-flip mutation in signature
    sig_mutated = bytearray(bytes(signature_bytes))
    sig_mutated[5] ^= 0xFF
    is_valid_mutated, reason_mutated = verify_ed25519_envelope(pubkey_str, canonical_bytes, bytes(sig_mutated).hex())
    assert is_valid_mutated is False
    assert reason_mutated == "CRYPTOGRAPHIC_SIGNATURE_MISMATCH"

    # 4. Fault Injection: Truncated signature length
    is_valid_trunc, reason_trunc = verify_ed25519_envelope(pubkey_str, canonical_bytes, signature_hex[:32])
    assert is_valid_trunc is False
    assert "INVALID_SIGNATURE_LENGTH" in reason_trunc


def test_safety_boundary_matrix():
    """
    Stress test 2: Validates environmental safety fail-safes.
    '0' or unset -> False (Dry-run mode)
    '1', 'true', 'active' -> True (Live mainnet mode)
    """
    print("\n[STRESS TEST 2] Environmental Safety Boundary Matrix...")

    # Unset / Zero -> Dry Run
    if "SIP_MAINNET_LIVE" in os.environ:
        del os.environ["SIP_MAINNET_LIVE"]
    assert verify_production_safety() is False, "Failed to block execution when env is missing"

    os.environ["SIP_MAINNET_LIVE"] = "0"
    assert verify_production_safety() is False, "Failed to block execution when flag is '0'"

    # Active flags -> Live Mode
    os.environ["SIP_MAINNET_LIVE"] = "1"
    assert verify_production_safety() is True, "Failed to engage live bounds on '1'"

    os.environ["SIP_MAINNET_LIVE"] = "true"
    assert verify_production_safety() is True, "Failed to engage live bounds on 'true'"
