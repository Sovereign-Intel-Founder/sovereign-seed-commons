import os
import time
import hashlib
import tempfile
import pytest
from solders.keypair import Keypair

from tollbridge.security import (
    build_canonical_envelope_bytes,
    verify_timestamp_freshness,
    validate_solana_pubkey,
    verify_ed25519_envelope
)
from tollbridge.ingress_metering import IngressMeteringEngine


@pytest.mark.asyncio
class TestIngressUnitSuite:

    @pytest.fixture
    def setup_engine(self):
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        engine = IngressMeteringEngine(db_path=db_path, max_queue_depth=100, batch_size=10)
        yield engine, db_path
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

    async def test_canonical_envelope_field_binding(self, setup_engine):
        """
        Verifies that any mutation to any of the canonical envelope fields
        invalidates the signature and is rejected by the engine.
        """
        engine, _ = setup_engine
        await engine.start()

        signer = Keypair()
        pubkey_str = str(signer.pubkey())
        raw_payload = b"CANONICAL_ENVELOPE_TEST_DATA"
        payload_hash = hashlib.sha256(raw_payload).hexdigest()
        
        protocol_version = "sip-v1.0"
        nonce = "nonce_canonical_001"
        timestamp = time.time()
        asset_type = "SOL"
        subscription_topic = "telemetry.v1"
        content_type = "application/octet-stream"

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
        sig_bytes = signer.sign_message(canonical_bytes)
        signature_hex = bytes(sig_bytes).hex()

        # 1. Valid submission passes cleanly
        res = await engine.submit_envelope_payload(
            protocol_version=protocol_version,
            client_pubkey=pubkey_str,
            nonce=nonce,
            timestamp_sec=timestamp,
            asset_type=asset_type,
            subscription_topic=subscription_topic,
            content_type=content_type,
            raw_payload=raw_payload,
            signature_hex=signature_hex
        )
        assert res["status"] == "accepted", f"Expected accepted, got {res}"

        # 2. Tampering with payload fails signature check
        res_tampered_payload = await engine.submit_envelope_payload(
            protocol_version=protocol_version,
            client_pubkey=pubkey_str,
            nonce="nonce_canonical_002",
            timestamp_sec=timestamp,
            asset_type=asset_type,
            subscription_topic=subscription_topic,
            content_type=content_type,
            raw_payload=b"ALTERED_PAYLOAD_DATA",
            signature_hex=signature_hex
        )
        assert res_tampered_payload["status"] == "rejected"
        assert res_tampered_payload["reason"] == "CRYPTOGRAPHIC_SIGNATURE_MISMATCH"

        # 3. Tampering with asset_type fails signature check
        res_tampered_asset = await engine.submit_envelope_payload(
            protocol_version=protocol_version,
            client_pubkey=pubkey_str,
            nonce="nonce_canonical_003",
            timestamp_sec=timestamp,
            asset_type="USDC",
            subscription_topic=subscription_topic,
            content_type=content_type,
            raw_payload=raw_payload,
            signature_hex=signature_hex
        )
        assert res_tampered_asset["status"] == "rejected"
        assert res_tampered_asset["reason"] == "CRYPTOGRAPHIC_SIGNATURE_MISMATCH"

        # 4. Tampering with subscription_topic fails signature check
        res_tampered_topic = await engine.submit_envelope_payload(
            protocol_version=protocol_version,
            client_pubkey=pubkey_str,
            nonce="nonce_canonical_004",
            timestamp_sec=timestamp,
            asset_type=asset_type,
            subscription_topic="telemetry.v2",
            content_type=content_type,
            raw_payload=raw_payload,
            signature_hex=signature_hex
        )
        assert res_tampered_topic["status"] == "rejected"
        assert res_tampered_topic["reason"] == "CRYPTOGRAPHIC_SIGNATURE_MISMATCH"

        await engine.stop()

    async def test_stale_timestamp_rejection(self, setup_engine):
        """
        Verifies that payloads outside the drift window are rejected before cryptographic checks.
        """
        engine, _ = setup_engine
        await engine.start()

        signer = Keypair()
        pubkey_str = str(signer.pubkey())
        raw_payload = b"STALE_TIMESTAMP_TEST"
        payload_hash = hashlib.sha256(raw_payload).hexdigest()
        
        stale_timestamp = time.time() - 1000.0  # Outside 300s drift window
        nonce = "nonce_stale_001"

        canonical_bytes = build_canonical_envelope_bytes(
            "sip-v1.0", pubkey_str, nonce, stale_timestamp,
            "SOL", payload_hash, "application/octet-stream", "telemetry.v1"
        )
        signature_hex = bytes(signer.sign_message(canonical_bytes)).hex()

        res = await engine.submit_envelope_payload(
            protocol_version="sip-v1.0",
            client_pubkey=pubkey_str,
            nonce=nonce,
            timestamp_sec=stale_timestamp,
            asset_type="SOL",
            subscription_topic="telemetry.v1",
            content_type="application/octet-stream",
            raw_payload=raw_payload,
            signature_hex=signature_hex
        )

        assert res["status"] == "rejected"
        assert res["reason"] == "TIMESTAMP_STALE"

        await engine.stop()

    async def test_durable_nonce_replay_and_restart(self, setup_engine):
        """
        Tests that nonces cannot be replayed, and that idempotency state 
        persists across engine restarts on the same SQLite database file.
        """
        engine, db_path = setup_engine
        await engine.start()

        signer = Keypair()
        pubkey_str = str(signer.pubkey())
        raw_payload = b"REPLAY_RESTART_TEST"
        payload_hash = hashlib.sha256(raw_payload).hexdigest()
        
        protocol_version = "sip-v1.0"
        nonce = "nonce_durable_100"
        timestamp = time.time()
        asset_type = "SOL"
        subscription_topic = "telemetry.v1"
        content_type = "application/octet-stream"

        canonical_bytes = build_canonical_envelope_bytes(
            protocol_version, pubkey_str, nonce, timestamp, 
            asset_type, payload_hash, content_type, subscription_topic
        )
        signature_hex = bytes(signer.sign_message(canonical_bytes)).hex()

        # First valid submission
        res1 = await engine.submit_envelope_payload(
            protocol_version, pubkey_str, nonce, timestamp, asset_type, 
            subscription_topic, content_type, raw_payload, signature_hex
        )
        assert res1["status"] == "accepted"

        # Immediate replay check (Conflict)
        res2 = await engine.submit_envelope_payload(
            protocol_version, pubkey_str, nonce, timestamp, asset_type, 
            subscription_topic, content_type, raw_payload, signature_hex
        )
        assert res2["status"] == "rejected"
        assert res2["reason"] == "NONCE_REPLAY_DETECTED"

        await engine.stop()

        # Simulate hard crash/shutdown and restart pointing to the same SQLite vault
        restarted_engine = IngressMeteringEngine(db_path=db_path)
        await restarted_engine.start()

        # Submit again after restart (Proves persistent SQLite idempotency table)
        res3 = await restarted_engine.submit_envelope_payload(
            protocol_version, pubkey_str, nonce, timestamp, asset_type, 
            subscription_topic, content_type, raw_payload, signature_hex
        )
        assert res3["status"] == "rejected"
        assert res3["reason"] == "NONCE_REPLAY_DETECTED"

        await restarted_engine.stop()
