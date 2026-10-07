import hashlib
import logging
from typing import Dict, Any, Tuple, Final
from tollbridge.security import verify_ed25519_envelope, verify_timestamp_freshness, build_canonical_envelope_bytes

logger = logging.getLogger("SIP.RemoteHandoffValidator")

class RemoteHandoffValidator:
    __slots__ = ()

    REQUIRED_FIELDS: Final[tuple] = (
        "protocol_version", "client_pubkey", "nonce",
        "timestamp_sec", "asset_type", "subscription_topic",
        "content_type", "signature_hex"
    )

    @classmethod
    def validate_remote_envelope(
        cls, envelope_data: Dict[str, Any], raw_payload: bytes
    ) -> Tuple[bool, str]:
        if not envelope_data or not isinstance(envelope_data, dict):
            return False, "REMOTE_MALFORMED_ENVELOPE_TYPE"

        missing_fields = [f for f in cls.REQUIRED_FIELDS if f not in envelope_data]
        if missing_fields:
            return False, f"REMOTE_MISSING_FIELDS_{'_'.join(missing_fields)}"

        try:
            protocol_version = str(envelope_data["protocol_version"])
            client_pubkey = str(envelope_data["client_pubkey"])
            nonce = str(envelope_data["nonce"])
            timestamp_sec = float(envelope_data["timestamp_sec"])
            asset_type = str(envelope_data["asset_type"])
            subscription_topic = str(envelope_data["subscription_topic"])
            content_type = str(envelope_data["content_type"])
            signature_hex = str(envelope_data["signature_hex"])
        except (ValueError, TypeError):
            return False, "REMOTE_HEADER_TYPE_CAST_FAULT"

        if not verify_timestamp_freshness(timestamp_sec):
            return False, "REMOTE_TIMESTAMP_STALE"

        try:
            payload_hash = hashlib.sha256(raw_payload).hexdigest()
            canonical_bytes = build_canonical_envelope_bytes(
                protocol_version=protocol_version,
                client_pubkey=client_pubkey,
                nonce=nonce,
                timestamp=timestamp_sec,
                asset_type=asset_type,
                payload_hash=payload_hash,
                content_type=content_type,
                subscription_topic=subscription_topic
            )
        except Exception:
            return False, "REMOTE_CANONICAL_BUILD_FAULT"

        is_valid, reason = verify_ed25519_envelope(
            client_pubkey=client_pubkey,
            canonical_bytes=canonical_bytes,
            signature_hex=signature_hex
        )

        if not is_valid:
            return False, f"REMOTE_{reason}"

        return True, "OK"
