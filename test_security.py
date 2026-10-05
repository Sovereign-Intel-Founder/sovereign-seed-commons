import unittest
import asyncio
from commons_bridge.adapters import LocalLoopbackJsonRpcAdapter

class TestSecurityEnforcement(unittest.IsolatedAsyncioTestCase):
    async def test_non_loopback_rejection(self):
        # Attempt to initialize with an external IP to verify strict security boundary
        adapter = LocalLoopbackJsonRpcAdapter({"host": "192.168.1.100"})
        with self.assertRaises(ValueError):
            await adapter.initialize()

if __name__ == "__main__":
    unittest.main()
