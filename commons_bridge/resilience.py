import asyncio
import random
import logging
from typing import AsyncGenerator, Dict, Any

logger = logging.getLogger("SandboxResilience")

async def stress_inject_stream(
    stream_gen: AsyncGenerator[Dict[str, Any], None], 
    inject_errors: bool = True,
    jitter_ms: float = 5.0
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Wraps an adapter's stream generator to inject artificial jitter, 
    latency variations, and malformed payload tests for pipeline resilience training.
    """
    async for packet in stream_gen:
        # Simulate network jitter/latency
        if jitter_ms > 0:
            delay = random.uniform(0.001, jitter_ms / 1000.0)
            await asyncio.sleep(delay)
            
        # Optionally inject a malformed payload test case to check error handling
        if inject_errors and random.random() < 0.1:  # 10% chance of fault injection
            yield {"source": "sandbox_fault_injector", "status": "malformed_packet_test", "payload": None}
        else:
            # Pass through original packet with added resilience metadata
            packet["resilience_tested"] = True
            yield packet
