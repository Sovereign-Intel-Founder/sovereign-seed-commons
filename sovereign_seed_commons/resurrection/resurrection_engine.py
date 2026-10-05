import json
import logging
import os
import hashlib
from typing import Dict, Any, Tuple, Final

logger = logging.getLogger("SIP.ResurrectionEngine")

class ResurrectionEngine:
    """
    Manages Git-native state checkpointing, persistence, and atomic resurrection
    for autonomous protocol cells.
    """

    __slots__ = ()

    @staticmethod
    def create_checkpoint(cell_id: str, state_data: Dict[str, Any], checkpoint_dir: str = "/tmp/sip_checkpoints") -> Tuple[bool, str]:
        """
        Creates a cryptographically hashed checkpoint file for a protocol cell's state.
        """
        try:
            os.makedirs(checkpoint_dir, exist_ok=True)
            normalized_state = json.dumps(state_data, sort_keys=True, separators=(',', ':'))
            state_hash = hashlib.sha256(normalized_state.encode('utf-8')).hexdigest()
            
            checkpoint_payload = {
                "cell_id": cell_id,
                "state_hash": state_hash,
                "state_data": state_data
            }
            
            file_path = os.path.join(checkpoint_dir, f"{cell_id}_checkpoint.json")
            with open(file_path, "w") as f:
                json.dump(checkpoint_payload, f, indent=2)
                
            logger.info(f"[RESURRECTION] Checkpoint created successfully for cell {cell_id} [Hash: {state_hash[:16]}...]...")
            return True, state_hash
        except Exception as exc:
            logger.error(f"[RESURRECTION] Failed to create checkpoint for cell {cell_id}: {exc}")
            return False, ""

    @staticmethod
    def resurrect_state(cell_id: str, checkpoint_dir: str = "/tmp/sip_checkpoints") -> Tuple[bool, Dict[str, Any], str]:
        """
        Resurrects and validates a protocol cell's state from its persistent checkpoint.
        """
        file_path = os.path.join(checkpoint_dir, f"{cell_id}_checkpoint.json")
        if not os.path.exists(file_path):
            logger.warning(f"[RESURRECTION] No checkpoint found for cell {cell_id} at {file_path}")
            return False, {}, "RESURRECTION_CHECKPOINT_NOT_FOUND"

        try:
            with open(file_path, "r") as f:
                checkpoint_payload = json.load(f)

            stored_hash = checkpoint_payload.get("state_hash")
            state_data = checkpoint_payload.get("state_data")

            if not stored_hash or not isinstance(state_data, dict):
                return False, {}, "RESURRECTION_MALFORMED_CHECKPOINT"

            # Re-verify integrity via hash computation
            normalized_state = json.dumps(state_data, sort_keys=True, separators=(',', ':'))
            computed_hash = hashlib.sha256(normalized_state.encode('utf-8')).hexdigest()

            if computed_hash != stored_hash:
                logger.error(f"[RESURRECTION] Checkpoint integrity failure for cell {cell_id}! Hash mismatch.")
                return False, {}, "RESURRECTION_INTEGRITY_MISMATCH"

            logger.info(f"[RESURRECTION] Successfully resurrected state for cell {cell_id}.")
            return True, state_data, "OK"
        except Exception as exc:
            logger.error(f"[RESURRECTION] Runtime exception during state resurrection for cell {cell_id}: {exc}")
            return False, {}, "RESURRECTION_RUNTIME_EXCEPTION"
