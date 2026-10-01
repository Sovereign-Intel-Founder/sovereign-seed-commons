import hashlib
import json
import logging
from typing import Dict, Any, Tuple, Final

logger = logging.getLogger("SIP.EvidenceValidator")

class EvidenceValidator:
    """
    Validates evidence returns from autonomous protocol cells against expected cryptographic hashes.
    """

    __slots__ = ()

    @staticmethod
    def compute_evidence_hash(evidence_payload: Dict[str, Any]) -> str:
        """
        Computes a deterministic SHA-256 hash of the normalized evidence payload.
        """
        try:
            normalized_bytes = json.dumps(evidence_payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
            return hashlib.sha256(normalized_bytes).hexdigest()
        except Exception as exc:
            logger.error(f"[EVIDENCE] Failed to serialize and hash evidence payload: {exc}")
            return ""

    @classmethod
    def verify_evidence(cls, evidence_payload: Dict[str, Any], expected_hash: str) -> Tuple[bool, str]:
        """
        Verifies that an execution evidence payload matches the expected cryptographic commitment.
        """
        if not evidence_payload or not isinstance(evidence_payload, dict):
            return False, "EVIDENCE_MALFORMED_PAYLOAD"

        if not expected_hash or not isinstance(expected_hash, str):
            return False, "EVIDENCE_INVALID_EXPECTED_HASH"

        computed_hash = cls.compute_evidence_hash(evidence_payload)
        if not computed_hash:
            return False, "EVIDENCE_COMPUTATION_FAULT"

        if computed_hash != expected_hash:
            logger.warning(f"[EVIDENCE] Hash mismatch! Computed: {computed_hash}, Expected: {expected_hash}")
            return False, "EVIDENCE_HASH_MISMATCH"

        return True, "OK"
