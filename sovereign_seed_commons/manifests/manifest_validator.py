import hashlib
import logging
from typing import Dict, Any, Tuple, Final
from tollbridge.security import verify_ed25519_envelope

logger = logging.getLogger("SIP.CommonsManifestValidator")

class CommonsManifestValidator:
    """
    Production-grade cryptographically bound task manifest validator for sovereign-seed-commons.
    Enforces strict structural contracts, Ed25519 cell signatures, and immutable payload bindings.
    """

    __slots__ = ()

    REQUIRED_MANIFEST_FIELDS: Final[tuple] = (
        "manifest_version",
        "cell_id",
        "client_pubkey",
        "task_type",
        "target_resource",
        "execution_timeout_sec",
        "expected_evidence_hash",
        "timestamp_sec",
        "signature_hex"
    )

    @classmethod
    def _build_canonical_manifest_bytes(cls, manifest: Dict[str, Any]) -> bytes:
        """
        Constructs a deterministic canonical byte representation of the manifest 
        for cryptographic signature verification.
        """
        canonical_str = (
            f"version:{manifest['manifest_version']}|"
            f"cell:{manifest['cell_id']}|"
            f"pubkey:{manifest['client_pubkey']}|"
            f"task:{manifest['task_type']}|"
            f"resource:{manifest['target_resource']}|"
            f"timeout:{manifest['execution_timeout_sec']}|"
            f"evidence_hash:{manifest['expected_evidence_hash']}|"
            f"timestamp:{manifest['timestamp_sec']}"
        )
        return canonical_str.encode('utf-8')

    @classmethod
    def validate_manifest(cls, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Performs zero-trust schema validation and Ed25519 cryptographic signature verification
        on an autonomous protocol cell task manifest.
        """
        if not manifest or not isinstance(manifest, dict):
            return False, "MANIFEST_MALFORMED_TYPE"

        missing = [f for f in cls.REQUIRED_MANIFEST_FIELDS if f not in manifest]
        if missing:
            logger.debug(f"[COMMONS] Manifest schema violation. Missing: {missing}")
            return False, f"MANIFEST_MISSING_FIELDS_{'_'.join(missing)}"

        try:
            version = str(manifest["manifest_version"])
            cell_id = str(manifest["cell_id"])
            client_pubkey = str(manifest["client_pubkey"])
            task_type = str(manifest["task_type"])
            target_resource = str(manifest["target_resource"])
            timeout = float(manifest["execution_timeout_sec"])
            expected_evidence_hash = str(manifest["expected_evidence_hash"])
            timestamp_sec = float(manifest["timestamp_sec"])
            signature_hex = str(manifest["signature_hex"])
        except (ValueError, TypeError) as exc:
            logger.debug(f"[COMMONS] Type casting fault in manifest header: {exc}")
            return False, "MANIFEST_TYPE_CAST_FAULT"

        if timeout <= 0.0 or timeout > 3600.0:
            return False, "MANIFEST_INVALID_TIMEOUT_BOUNDS"

        try:
            canonical_bytes = cls._build_canonical_manifest_bytes(manifest)
        except Exception as exc:
            logger.error(f"[COMMONS] Failed to build canonical manifest bytes: {exc}")
            return False, "MANIFEST_CANONICAL_BUILD_FAULT"

        is_valid, reason = verify_ed25519_envelope(
            client_pubkey=client_pubkey,
            canonical_bytes=canonical_bytes,
            signature_hex=signature_hex
        )

        if not is_valid:
            logger.warning(f"[COMMONS] Manifest signature rejection for cell {cell_id}: {reason}")
            return False, f"MANIFEST_{reason}"

        return True, "OK"
