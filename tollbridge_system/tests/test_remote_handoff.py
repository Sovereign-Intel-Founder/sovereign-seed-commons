import time
import hashlib
import pytest
from solders.keypair import Keypair

from tollbridge.security import build_canonical_envelope_bytes
from sip_remote_handoff.validator import RemoteHandoffValidator


def test_valid_remote_handoff():
    signer = Keypair()
    pubkey_str = str(signer.pubkey())
    
    protocol_version = "sip-v1.0"
    nonce = "handoff_nonce_001"
    timestamp = time.time()
    asset_type = "SOL"
    subscription_topic = "mesh.sync"
    content_type = "application/json"
    
    raw_payload = b'{"status": "sync_ok", "node": "alpha"}'
    payload_hash = hashlib.sha256(raw_payload).hexdigest()

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

    envelope_data = {
        "protocol_version": protocol_version,
        "client_pubkey": pubkey_str,
        "nonce": nonce,
        "timestamp_sec": timestamp,
        "asset_type": asset_type,
        "subscription_topic": subscription_topic,
        "content_type": content_type,
        "signature_hex": signature_hex
    }

    is_valid, reason = RemoteHandoffValidator.validate_remote_envelope(envelope_data, raw_payload)
    assert is_valid is True, f"Valid remote handoff failed: {reason}"
    assert reason == "OK"


def test_remote_handoff_stale_timestamp():
    signer = Keypair()
    pubkey_str = str(signer.pubkey())
    
    # Timestamp outside 300s window (e.g., 10 minutes in the past)
    stale_timestamp = time.time() - 400.0
    
    envelope_data = {
        "protocol_version": "sip-v1.0",
        "client_pubkey": pubkey_str,
        "nonce": "hando_nonce_002",
        "timestamp_sec": stale_timestamp,
        "asset_type": "SOL",
        "subscription_topic": "mesh.sync",
        "content_type": "application/json",
        "signature_hex": "deadbeef" * 16
    }

    is_valid, reason = RemoteHandoffValidator.validate_remote_envelope(envelope_data, b"payload")
    assert is_valid is False
    assert reason == "REMOTE_TIMESTAMP_STALE"


def test_remote_handoff_missing_fields():
    envelope_data = {
        "protocol_version": "sip-v1.0"
        # Missing required fields
    }

    is_valid, reason = RemoteHandoffValidator.validate_remote_envelope(envelope_data, b"payload")
    assert is_valid is False
    assert "REMOTE_MISSING_FIELDS" in reason
