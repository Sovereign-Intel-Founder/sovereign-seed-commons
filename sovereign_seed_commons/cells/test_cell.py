import time
import pytest
import asyncio
from solders.keypair import Keypair

from cells.cell_executor import ProtocolCellExecutor
from evidence.evidence_validator import EvidenceValidator

@pytest.mark.asyncio
async def test_cell_execution_success():
    signer = Keypair()
    pubkey_str = str(signer.pubkey())
    
    # Pre-calculate what the cell payload will return so we can set the expected hash in the manifest
    dummy_payload = {
        "cell_id": "cell_runtime_01",
        "execution_status": "SUCCESS",
        "metrics": {
            "ops_completed": 100,
            "latency_ms": 0.52
        },
        "output_state": "state_checkpoint_verified"
    }
    expected_hash = EvidenceValidator.compute_evidence_hash(dummy_payload)

    manifest = {
        "manifest_version": "v1.0",
        "cell_id": "cell_runtime_01",
        "client_pubkey": pubkey_str,
        "task_type": "autonomous_execution",
        "target_resource": "git://commons/runtime.git",
        "execution_timeout_sec": 5.0,
        "expected_evidence_hash": expected_hash,
        "timestamp_sec": time.time()
    }
    
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
    signature_bytes = signer.sign_message(canonical_str.encode('utf-8'))
    manifest["signature_hex"] = bytes(signature_bytes).hex()

    success, payload, reason = await ProtocolCellExecutor.execute_cell(manifest)
    
    assert success is True
    assert reason == "OK"
    assert payload["cell_id"] == "cell_runtime_01"
    assert payload["execution_status"] == "SUCCESS"
