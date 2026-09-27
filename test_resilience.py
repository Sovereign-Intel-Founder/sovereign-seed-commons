import unittest
import asyncio
from commons_bridge.adapters.json_rpc_adapter import LocalLoopbackJsonRpcAdapter
from commons_bridge.resilience import stress_inject_stream

class TestResilienceInjector(unittest.IsolatedAsyncioTestCase):
    async def test_stress_wrapper(self):
        adapter = LocalLoopbackJsonRpcAdapter({"host": "127.0.0.1"})
        await adapter.initialize()
        
        packets = []
        async for packet in stress_inject_stream(adapter.stream_data(), inject_errors=True, jitter_ms=1.0):
            packets.append(packet)
            if len(packets) >= 10:
                break
                
        await adapter.stop()
        self.assertGreater(len(packets), 0)
        # Verify either normal packets or injected fault packets are captured
        self.assertTrue(any("resilience_tested" in p or p.get("status") == "malformed_packet_test" for p in packets))

if __name__ == "__main__":
    unittest.main()
