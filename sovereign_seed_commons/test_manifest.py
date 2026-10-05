import time
import pytest
from solders.keypair import Keypair

from manifests.manifest_validator import CommonsManifestValidator

def test_valid_signed_manifest():
    signer = Keypair()
    pubkey_str = str(signer.pubkey())
    
    manifest = {
        "manifest_version": "v1.0",
        "cell_id": "cell_alpha_01",
        "client_pubkey": pubkey_str,
        "task_type": "state_resurrection",
        "target_resource": "git://commons/repo.git",
        "execution_timeout_sec": 30.0,
        "expected_evidence_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "timestamp_sec": time.time()
    }
    
    # Build canonical bytes matching the validator's exact format
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
    canonical_bytes = canonical_str.encode('utf-8')
    
    signature_bytes = signer.sign_message(canonical_bytes)
    manifest["signature_hex"] = bytes(signature_bytes).hex()

    is_valid, reason = CommonsManifestValidator.validate_manifest(manifest)
    assert is_valid is True, f"Valid signed manifest failed: {reason}"
    assert reason == "OK"

def test_manifest_invalid_timeout():
    manifest = {
        "manifest_version": "v1.0",
        "cell_id": "cell_alpha_01",
        "client_pubkey": "deadbeef" * 4,
        "task_type": "state_resurrection",
        "target_resource": "git://commons/repo.git",
        "execution_timeout_sec": 5000.0,  # Exceeds max bounds
        "expected_evidence_hash": "abc",
        "timestamp_sec": time.time(),
        "signature_hex": "deadbeef" * 16
    }
    is_valid, reason = CommonsManifestValidator.validate_manifest(manifest)
    assert is_valid is False
    assert reason == "MANIFEST_INVALID_TIMEOUT_BOUNDS"
