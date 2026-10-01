import json
import logging
from typing import Dict, Any, Optional
from tollbridge.ingress_metering import IngressMeteringEngine

logger = logging.getLogger("SIP.BridgeRouter")

class BridgeRouter:
    """
    Enterprise bridge router linking external ingestion requests
    to the underlying IngressMeteringEngine and security pipeline.
    """
    def __init__(self, engine: IngressMeteringEngine):
        self.engine = engine

    async def route_ingress(self, request_body: Dict[Any, Any]) -> Dict[str, Any]:
        """
        Routes an incoming JSON payload containing pubkey, raw_payload (hex),
        signature, nonce, and asset type through the metering engine.
        """
        try:
            client_pubkey = request_body.get("client_pubkey")
            raw_hex = request_body.get("payload_hex", "")
            signature_hex = request_body.get("signature_hex")
            nonce = request_body.get("nonce")
            asset_type = request_body.get("asset_type", "SOL")
            timestamp_sec = request_body.get("timestamp_sec")

            if not all([client_pubkey, raw_hex, signature_hex, nonce]):
                return {"status": "rejected", "code": 400, "reason": "MISSING_MANDATORY_FIELDS"}

            raw_payload = bytes.fromhex(raw_hex)

            result = await self.engine.submit_payload(
                client_pubkey=client_pubkey,
                raw_payload=raw_payload,
                signature_hex=signature_hex,
                nonce=nonce,
                asset_type=asset_type,
                timestamp_sec=timestamp_sec
            )
            return result

        except ValueError as ve:
            logger.error(f"[BRIDGE ERROR] Invalid hex decoding: {ve}")
            return {"status": "rejected", "code": 400, "reason": "INVALID_HEX_ENCODING"}
        except Exception as e:
            logger.error(f"[BRIDGE ERROR] Route execution exception: {e}")
            return {"status": "rejected", "code": 500, "reason": "INTERNAL_ROUTER_FAULT"}
