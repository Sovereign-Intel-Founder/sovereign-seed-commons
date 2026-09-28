"""
Sovereign Seed Commons - Bridge Module
"""

import sys
import os
import logging

HOST = os.getenv("COMMONS_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("COMMONS_BRIDGE_PORT", "8080"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("commons_bridge")

class SafeParticipantHandler:
    """Handles participant validation, message routing, and boundary checks."""
    def __init__(self, host=HOST, port=PORT):
        # Enforce strict local loopback binding
        if host not in ("127.0.0.1", "localhost"):
            logger.warning(f"Restricting host {host} to loopback 127.0.0.1")
            host = "127.0.0.1"
        self.host = host
        self.port = port
        self.active = True

    def validate_participant(self, participant_id: str) -> bool:
        if not participant_id or not isinstance(participant_id, str):
            return False
        return True

    def process_message(self, payload: dict) -> bool:
        if not self.active or not isinstance(payload, dict):
            return False
        logger.info(f"Processing bridge payload type: {payload.get('type', 'unknown')}")
        return True

def main():
    logger.info(f"Sovereign Seed Commons Bridge Active on {HOST}:{PORT}")
    handler = SafeParticipantHandler()
    print("Bridge initialized successfully.")

if __name__ == "__main__":
    main()
