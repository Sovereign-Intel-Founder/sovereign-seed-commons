"""
Sovereign Intelligence Protocol (SIP) - Enterprise Security & Cryptographic Verification Engine

Provides production-grade Ed25519 signature verification, Solana Base58 pubkey validation,
SHA-256 canonical payload verification, timestamp freshness gating, and mainnet safety controls.
"""

import os
import time
import hashlib
import logging
from typing import Optional, Tuple
import nacl.signing
import nacl.exceptions
from solders.pubkey import Pubkey

logger = logging.getLogger("SIP.Security")

# Security Constraints
MAX_TIMESTAMP_DRIFT_SEC: float = 300.0  # 5-minute replay window
ED25519_SIGNATURE_BYTES_LEN: int = 64


class SecurityValidationError(Exception):
    """Base exception for all security boundary failures."""
    pass


class InvalidSignatureError(SecurityValidationError):
    """Raised when Ed25519 signature fails cryptographic verification."""
    pass


class MalformedPayloadError(SecurityValidationError):
    """Raised when payload attributes fail structure or decoding checks."""
    pass


def verify_production_safety() -> bool:
    """
    Enforces environmental safety controls for live Solana mainnet interaction.
    Fail-safe design: Only explicitly setting '1' allows live execution.
    """
    mainnet_flag = os.getenv("SIP_MAINNET_LIVE", "0").strip()
    
    if mainnet_flag == "1":
        logger.info("[SAFETY GATE] LIVE MAINNET INGRESS ACTIVE. Settlement enabled.")
        return True
        
    logger.warning(f"[SAFETY GATE] SIP_MAINNET_LIVE='{mainnet_flag}'. Operating in restricted dry-run mode.")
    return False


def validate_solana_pubkey(pubkey_str: str) -> Optional[Pubkey]:
    """
    Parses and validates a Base58-encoded Solana public key.
    
    Args:
        pubkey_str: Base58 public key string.
        
    Returns:
        Pubkey object if valid, None if malformed.
    """
    if not pubkey_str or not isinstance(pubkey_str, str):
        logger.error("[PUBKEY VALIDATION] Public key string is empty or invalid type.")
        return None

    try:
        return Pubkey.from_string(pubkey_str.strip())
    except Exception as e:
        logger.error(f"[PUBKEY VALIDATION] Invalid Base58 Solana public key '{pubkey_str}': {e}")
        return None


def verify_timestamp_freshness(
    timestamp_sec: float,
    max_drift_sec: float = MAX_TIMESTAMP_DRIFT_SEC
) -> bool:
    """
    Validates that request timestamp falls within the allowed execution window.
    
    Args:
        timestamp_sec: Epoch timestamp (in seconds) provided in payload.
        max_drift_sec: Maximum allowable time difference in seconds.
        
    Returns:
        bool: True if timestamp is fresh, False if expired or far future.
    """
    current_time = time.time()
    drift = abs(current_time - timestamp_sec)
    
    if drift > max_drift_sec:
        logger.error(
            f"[REPLAY GATE] Timestamp drift exceeded: drift={drift:.2f}s, max={max_drift_sec}s"
        )
        return False
    return True


def verify_canonical_hash(payload_bytes: bytes, expected_hash_hex: str) -> bool:
    """
    Validates payload integrity against a provided canonical SHA-256 digest.
    
    Args:
        payload_bytes: Raw bytes of the payload.
        expected_hash_hex: Hex-encoded SHA-256 digest expected.
        
    Returns:
        bool: True if calculated hash matches expected hash.
    """
    if not payload_bytes or not expected_hash_hex:
        return False

    computed_hash = hashlib.sha256(payload_bytes).hexdigest()
    if computed_hash.lower() != expected_hash_hex.strip().lower():
        logger.error(
            f"[INTEGRITY FAILURE] Canonical hash mismatch: expected={expected_hash_hex}, got={computed_hash}"
        )
        return False
    return True


def verify_ed25519_envelope(
    client_pubkey_str: str,
    message_bytes: bytes,
    signature_hex: str
) -> bool:
    """
    Cryptographically verifies an Ed25519 signed payload envelope against a client's public key.
    
    Args:
        client_pubkey_str: Base58-encoded Solana public key of signer.
        message_bytes: Raw payload byte array signed by client.
        signature_hex: Hexadecimal string representation of 64-byte Ed25519 signature.
        
    Returns:
        bool: True if signature is cryptographically valid, False on forgery or corruption.
    """
    if not client_pubkey_str or not message_bytes or not signature_hex:
        logger.error("[SECURITY REJECTION] Null parameter provided to cryptographic verification.")
        return False

    # 1. Parse Solana Pubkey
    pubkey = validate_solana_pubkey(client_pubkey_str)
    if pubkey is None:
        return False

    # 2. Decode Signature Bytes
    try:
        signature_bytes = bytes.fromhex(signature_hex.strip())
    except ValueError as ve:
        logger.error(f"[SECURITY REJECTION] Malformed hex in signature: {ve}")
        return False

    if len(signature_bytes) != ED25519_SIGNATURE_BYTES_LEN:
        logger.error(
            f"[SECURITY REJECTION] Invalid signature length: expected {ED25519_SIGNATURE_BYTES_LEN} bytes, got {len(signature_bytes)}"
        )
        return False

    # 3. Cryptographic Signature Verification
    try:
        verify_key = nacl.signing.VerifyKey(bytes(pubkey))
        verify_key.verify(message_bytes, signature_bytes)
        return True
    except nacl.exceptions.BadSignatureError:
        logger.error(f"[SECURITY REJECTION] Invalid signature for public key {client_pubkey_str}")
        return False
    except Exception as e:
        logger.error(f"[SECURITY REJECTION] Verification exception: {e}")
        return False


def validate_full_security_envelope(
    client_pubkey_str: str,
    message_bytes: bytes,
    signature_hex: str,
    timestamp_sec: Optional[float] = None,
    expected_hash_hex: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Master safety gate executing full multi-factor verification.
    
    Returns:
        Tuple[bool, str]: (is_valid, failure_reason)
    """
    if validate_solana_pubkey(client_pubkey_str) is None:
        return False, "INVALID_SOLANA_PUBLIC_KEY"

    if expected_hash_hex and not verify_canonical_hash(message_bytes, expected_hash_hex):
        return False, "CANONICAL_HASH_MISMATCH"

    if timestamp_sec is not None and not verify_timestamp_freshness(timestamp_sec):
        return False, "TIMESTAMP_DRIFT_EXCEEDED"

    if not verify_ed25519_envelope(client_pubkey_str, message_bytes, signature_hex):
        return False, "INVALID_ED25519_SIGNATURE"

    return True, "SUCCESS"
