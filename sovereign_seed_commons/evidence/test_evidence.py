import pytest
from evidence.evidence_validator import EvidenceValidator

def test_valid_evidence_verification():
    payload = {
        "cell_id": "cell_alpha_01",
        "execution_status": "SUCCESS",
        "metrics": {"ops": 500, "latency_ms": 1.2},
        "output_state": "checkpoint_hash_xyz"
    }
    
    expected_hash = EvidenceValidator.compute_evidence_hash(payload)
    is_valid, reason = EvidenceValidator.verify_evidence(payload, expected_hash)
    
    assert is_valid is True
    assert reason == "OK"

def test_evidence_hash_mismatch():
    payload = {
        "cell_id": "cell_alpha_01",
        "execution_status": "SUCCESS",
        "metrics": {"ops": 500, "latency_ms": 1.2}
    }
    
    tampered_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    is_valid, reason = EvidenceValidator.verify_evidence(payload, tampered_hash)
    
    assert is_valid is False
    assert reason == "EVIDENCE_HASH_MISMATCH"
