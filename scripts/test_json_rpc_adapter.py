import asyncio
import json
from commons_bridge.adapters.json_rpc_adapter import LocalloopbackJsonRpcAdapter

async def run_tests():
    adapter = LocalloopbackJsonRpcAdapter({"host": "127.0.0.1"})
    await adapter.initialize()

    print("=== TESTING SOVEREIGN_HEALTH ===")
    req1 = json.dumps({"jsonrpc": "2.0", "method": "sovereign_health", "id": 1})
    res1 = await adapter.handle_request(req1)
    print(json.dumps(res1, indent=2))

    print("\n=== TESTING SOVEREIGN_VALIDATE_CELL ===")
    req2 = json.dumps({"jsonrpc": "2.0", "method": "sovereign_validate_cell", "id": 2})
    res2 = await adapter.handle_request(req2)
    print(json.dumps(res2, indent=2))

    print("\n=== TESTING TELEMETRY STREAM ===")
    async for item in adapter.stream_data():
        print(json.dumps(item, indent=2))
        break

    await adapter.stop()

if __name__ == "__main__":
    asyncio.run(run_tests())
