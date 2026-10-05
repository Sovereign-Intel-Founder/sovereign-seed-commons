import os
import time
import hashlib
import json
import logging
import secrets
from typing import Dict, Any, Tuple, Optional
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from solders.pubkey import Pubkey

logger = logging.getLogger("SIP.Security")

# =============================================================================
# ENTERPRISE SECURITY BOUNDS & CONSTANTS
# =============================================================================
MAX_TIMESTAMP_DRIFT_SEC = 300.0
SUPPORTED_PROTOCOL_VERSIONS = {"sip-v1.0"}
SUPPORTED_ASSET_TYPES = {"SOL", "USDC", "DATA_FEED"}
MAX_NONCE_LENGTH = 128
MAX_TOPIC_LENGTH = 256
EXPECTED_SIGNATURE_LENGTH = 64


def verify_production_safety() -> bool:
    """
    Enforces strict environmental safety fail-safes. 
    Prevents dry-run test environments from connecting to live mainnet routing.
    """
    live_flag = os.getenv("SIP_MAINNET_LIVE", "0").strip().lower()
    if live_flag in ("1", "true", "yes", "active"):
        logger.warning("[SAFETY GATE] SIP_MAINNET_LIVE active. Live operational bounds enforced.")
        return True
    logger.info("[SAFETY GATE] SIP_MAINNET_LIVE='0'. Operating in restricted dry-run mode.")
    return False


def build_canonical_envelope_bytes(
    protocol_version: str,
    client_pubkey: str,
    nonce: str,
    timestamp: float,
    asset_type: str,
    payload_hash: str,
    content_type: str,
    subscription_topic: str
) -> bytes:
    """
    Constructs a deterministic, sorted, canonical JSON byte string representing 
    all security-bound fields of the telemetry/subscription envelope.
    
    Any mutation to any of these fields post-signature will result in a 
    completely different byte string, failing cryptographic verification.
    """
    canonical_dict = {
        "asset_type": str(asset_type).strip(),
        "client_pubkey": str(client_pubkey).strip(),
        "content_type": str(content_type).strip(),
        "nonce": str(nonce).strip(),
        "payload_hash": str(payload_hash).strip(),
        "protocol_version": str(protocol_version).strip(),
        "subscription_topic": str(subscription_topic).strip(),
        "timestamp": float(timestamp)
    }
    
    # Deterministic serialization: keys sorted alphabetically, no whitespace padding
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return canonical_json.encode("utf-8")


def verify_timestamp_freshness(timestamp_sec: float, max_drift: float = MAX_TIMESTAMP_DRIFT_SEC) -> bool:
    """
    Validates that a timestamp falls within the allowed clock drift window.
    Prevents ingestion of extremely stale payloads even if the signature is valid.
    """
    now = time.time()
    diff = abs(now - timestamp_sec)
    if diff > max_drift:
        logger.debug(f"[SECURITY] Timestamp drift exceeded. Diff: {diff}s, Max allowed: {max_drift}s")
        return False
    return True


def validate_solana_pubkey(pubkey_str: str) -> bool:
    """
    Validates that a string is a legitimate Base58 encoded Solana public key.
    Relies on `solders.pubkey` native Rust bindings for maximum exactness.
    """
    try:
        if not pubkey_str or not isinstance(pubkey_str, str):
            return False
        
        cleaned_pubkey = pubkey_str.strip()
        if len(cleaned_pubkey) < 32 or len(cleaned_pubkey) > 44:
            return False
            
        Pubkey.from_string(cleaned_pubkey)
        return True
    except Exception as e:
        logger.debug(f"[SECURITY] Solana public key validation failed: {e}")
        return False


def verify_payload_hash_constant_time(computed_hash: str, provided_hash: str) -> bool:
    """
    Uses Python's secrets.compare_digest to prevent timing attacks when verifying
    that the hash of the raw payload matches the hash bound inside the envelope.
    """
    return secrets.compare_digest(str(computed_hash).lower(), str(provided_hash).lower())


def verify_ed25519_envelope(
    client_pubkey: str,
    canonical_bytes: bytes,
    signature_hex: str
) -> Tuple[bool, str]:
    """
    Cryptographically verifies an Ed25519 signature against the canonical envelope bytes.
    
    Args:
        client_pubkey: The Base58 Solana public key string.
        canonical_bytes: The deterministic UTF-8 byte array of the bound envelope.
        signature_hex: The hex-encoded 64-byte Ed25519 signature.
        
    Returns:
        Tuple containing a boolean (True if valid) and a string reason code.
    """
    try:
        # 1. Pubkey Validation
        if not validate_solana_pubkey(client_pubkey):
            return False, "INVALID_SOLANA_PUBKEY"

        # 2. Signature Presence and Type Checking
        if not signature_hex or not isinstance(signature_hex, str):
            return False, "MISSING_OR_INVALID_SIGNATURE_TYPE"

        # 3. Hex Decoding & Length Hardening
        cleaned_sig_hex = signature_hex.strip()
        if len(cleaned_sig_hex) % 2 != 0:
            return False, "MALFORMED_HEX_SIGNATURE_ODD_LENGTH"
            
        sig_bytes = bytes.fromhex(cleaned_sig_hex)
        if len(sig_bytes) != EXPECTED_SIGNATURE_LENGTH:
            return False, f"INVALID_SIGNATURE_LENGTH_EXPECTED_{EXPECTED_SIGNATURE_LENGTH}"

        # 4. Core Cryptographic Verification via PyNaCl
        pubkey_obj = Pubkey.from_string(client_pubkey.strip())
        verify_key = VerifyKey(bytes(pubkey_obj))

        verify_key.verify(canonical_bytes, sig_bytes)
        return True, "OK"

    except ValueError as ve:
        logger.debug(f"[SECURITY] Hex decoding error in signature: {ve}")
        return False, "INVALID_HEX_ENCODING"
    except BadSignatureError:
        logger.warning(f"[SECURITY] Cryptographic signature mismatch for pubkey: {client_pubkey}")
        return False, "CRYPTOGRAPHIC_SIGNATURE_MISMATCH"
    except Exception as e:
        logger.error(f"[SECURITY] Unhandled verification fault: {e}")
        return False, "INTERNAL_VERIFICATION_FAULT"
