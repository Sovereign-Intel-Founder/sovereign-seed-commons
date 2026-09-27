import asyncio
from typing import AsyncGenerator, Dict, Any
from .base import BaseStreamAdapter

class LocalLoopbackJsonRpcAdapter(BaseStreamAdapter):
    """Secure loopback-only JSON-RPC / custom stream adapter enforcing 127.0.0.1 constraints."""

    async def initialize(self) -> bool:
        target_host = self.config.get("host", "127.0.0.1")
        if target_host != "127.0.0.1":
            raise ValueError("Safety violation: Commons adapters must bind strictly to 127.0.0.1.")
        return True

    async def stream_data(self) -> AsyncGenerator[Dict[str, Any], None]:
        self._running = True
        counter = 0
        while self._running and counter < 5:  # Bounded for test harness execution
            payload = {
                "adapter": "json_rpc_loopback",
                "sequence": counter,
                "status": "active_stream",
                "payload": {"metric": "simulated_rpc_signal", "value": 100.0 + counter}
            }
            yield payload
            counter += 1
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        self._running = False
