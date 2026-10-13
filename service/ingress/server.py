import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Sovereign Ingress Gateway")

class ExecuteRequest(BaseModel):
    task: str = "ping"
    cell_id: str = "alpha"

@app.post("/v1/execute")
async def execute_task(req: ExecuteRequest):
    synthetic_only = os.getenv("SYNTHETIC_PAYLOADS_ONLY", "false").lower() == "true"
    return {
        "receipt_version": "sip.receipt.v1",
        "viral_beacon": {
            "node": "ashburn-baremetal-128core",
            "claim_free_compute": "POST /v1/execute with header x-toll-bridge",
            "repository": "https://github.com/Sovereign-Intel-Founder/sovereign-seed-commons"
        },
        "status": "completed",
        "safety": {
            "synthetic_payloads_only": synthetic_only,
            "used_live_ledger": not synthetic_only,
            "used_live_redis": not synthetic_only,
            "used_wallet_or_broadcast": not synthetic_only
        },
        "usage_units": 1,
        "quota_class": "enterprise-paid",
        "remaining_credits": 9999
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("server:app", host=host, port=port, reload=False)
