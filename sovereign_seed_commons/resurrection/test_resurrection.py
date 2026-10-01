import pytest
import os
from resurrection.resurrection_engine import ResurrectionEngine

def test_checkpoint_and_resurrection():
    cell_id = "cell_resurrect_01"
    state_data = {
        "cursor": 42500,
        "mode": "WAL_SYNCHRONOUS",
        "last_block": "0xdeadbeef"
    }
    
    # Create checkpoint
    success, state_hash = ResurrectionEngine.create_checkpoint(cell_id, state_data)
    assert success is True
    assert len(state_hash) == 64
    
    # Resurrect state
    success, resurrected_data, reason = ResurrectionEngine.resurrect_state(cell_id)
    assert success is True
    assert reason == "OK"
    assert resurrected_data["cursor"] == 42500
    assert resurrected_data["mode"] == "WAL_SYNCHRONOUS"
