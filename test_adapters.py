import asyncio
import unittest
from commons_bridge.adapters import LocalLoopbackJsonRpcAdapter

class TestStreamAdapters(unittest.IsolatedAsyncioTestCase):
    async def test_json_rpc_adapter_flow(self):
        adapter = LocalLoopbackJsonRpcAdapter({"host": "127.0.0.1"})
        initialized = await adapter.initialize()
        self.assertTrue(initialized)

        results = []
        async for packet in adapter.stream_data():
            results.append(packet)

        await adapter.stop()
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]["adapter"], "json_rpc_loopback")
        self.assertEqual(results[0]["sequence"], 0)

if __name__ == "__main__":
    unittest.main()
