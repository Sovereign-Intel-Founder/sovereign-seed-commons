import unittest
import asyncio
from commons_bridge.loader import load_adapters_from_config

class TestLoader(unittest.TestCase):
    def test_dynamic_loading(self):
        adapters = load_adapters_from_config("commons_bridge/config.yaml")
        self.assertEqual(len(adapters), 1)
        self.assertEqual(adapters[0].config["host"], "127.0.0.1")

if __name__ == "__main__":
    unittest.main()
