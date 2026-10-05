import logging
from typing import Dict, Any

from tollbridge.ingress_metering import IngressMeteringEngine

logger = logging.getLogger("SIP.BridgeRouter")

class BridgeRouter:
    """
    Ingress Bridge Router for the Sovereign Intelligence Protocol.
    
    Acts as the primary protocol gateway and boundary enforcement layer between 
    the external API/network transport layer and the internal IngressMeteringEngine. 
    It strictly validates envelope schema, enforces structural size limits prior to 
    deserialization, safely decodes hexadecimal payloads into raw bytes, and routes 
    the sanitized request into the cryptographic execution pipeline.
    """
    
    # Strictly enforce a 2 MB absolute maximum size for incoming requests to prevent
    # memory exhaustion attacks (OOM) before payloads even hit the metering queue.
    MAX_PAYLOAD_SIZE_BYTES = 2 * 1024 * 1024

    def __init__(self, engine: IngressMeteringEngine):
        """
        Initializes the Bridge Router with a reference to the active metering engine.
        
        Args:
            engine: The booted IngressMeteringEngine instance.
        """
        self.engine = engine

    async def route_ingress(self, request_body: Dict[str, Any], raw_body_bytes_len: int) -> Dict[str, Any]:
        """
        Primary routing logic for incoming telemetry/execution envelopes.
        
        Args:
            request_body: The parsed JSON dictionary containing the envelope fields.
            raw_body_bytes_len: The pre-calculated byte length of the raw incoming request.
            
        Returns:
            A dictionary containing the resolution 'status' and 'reason'.
        """
        
        # 1. Pre-Decode Structural Size Boundary Enforcement
        if raw_body_bytes_len > self.MAX_PAYLOAD_SIZE_BYTES:
            logger.warning(
                f"[ROUTER] Request rejected. Payload size {raw_body_bytes_len} bytes "
                f"exceeds absolute limit of {self.MAX_PAYLOAD_SIZE_BYTES} bytes."
            )
            return {"status": "rejected", "reason": "PAYLOAD_TOO_LARGE"}

        # 2. Strict Schema Presence Validation
        required_fields = [
            "protocol_version",
            "client_pubkey",
            "nonce",
            "timestamp_sec",
            "asset_type",
            "subscription_topic",
            "content_type",
            "payload_hex",
            "signature_hex"
        ]
        
        missing_fields = [field for field in required_fields if field not in request_body]
        if missing_fields:
            logger.debug(f"[ROUTER] Schema violation. Missing fields: {missing_fields}")
            return {"status": "rejected", "reason": f"MISSING_FIELDS_{'_'.join(missing_fields)}"}

        # 3. Safe Extraction and Type Enforcement
        try:
            protocol_version = str(request_body["protocol_version"])
            client_pubkey = str(request_body["client_pubkey"])
            nonce = str(request_body["nonce"])
            timestamp_sec = float(request_body["timestamp_sec"])
            asset_type = str(request_body["asset_type"])
            subscription_topic = str(request_body["subscription_topic"])
            content_type = str(request_body["content_type"])
            payload_hex = str(request_body["payload_hex"])
            signature_hex = str(request_body["signature_hex"])
        except ValueError as ve:
            logger.debug(f"[ROUTER] Type casting failure during routing: {ve}")
            return {"status": "rejected", "reason": "MALFORMED_FIELD_TYPES"}

        # 4. Hexadecimal Decoding to Raw Bytes
        try:
            # We enforce an even-length hex string to prevent ValueError exceptions
            # from malformed representations in the transport layer.
            cleaned_hex = payload_hex.strip()
            if len(cleaned_hex) % 2 != 0:
                 return {"status": "rejected", "reason": "MALFORMED_PAYLOAD_HEX_ODD_LENGTH"}
                 
            raw_payload = bytes.fromhex(cleaned_hex)
        except ValueError:
            logger.debug("[ROUTER] Failed to decode payload_hex into raw bytes.")
            return {"status": "rejected", "reason": "INVALID_PAYLOAD_HEX_ENCODING"}

        # 5. Hand-off to the Cryptographic Ingestion Pipeline
        # At this stage, structural integrity is guaranteed. The engine handles
        # all cryptographic bounds, idempotency checks, and durable persistence.
        try:
            result = await self.engine.submit_envelope_payload(
                protocol_version=protocol_version,
                client_pubkey=client_pubkey,
                nonce=nonce,
                timestamp_sec=timestamp_sec,
                asset_type=asset_type,
                subscription_topic=subscription_topic,
                content_type=content_type,
                raw_payload=raw_payload,
                signature_hex=signature_hex
            )
            return result
        except Exception as e:
            logger.error(f"[ROUTER] Catastrophic failure routing to engine: {e}")
            return {"status": "rejected", "reason": "INTERNAL_ENGINE_ROUTING_FAULT"}
