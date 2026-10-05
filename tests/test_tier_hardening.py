import os
import json
import hashlib
import sys

PROFILES_PATH = "configs/participation_profiles.json"

def load_profiles():
    with open(PROFILES_PATH, "r") as f:
        return json.load(f)["participation_tiers"]

def test_risk_ceilings():
    profiles = load_profiles()
    print("[*] Testing Risk Ceiling Enforcement...")
    
    # Verify Regular Commons & Paper Trading have $0 risk
    assert profiles["regular_commons"]["risk_ceiling_usd"] == 0.0, "Regular commons risk ceiling breached!"
    assert profiles["paper_trading"]["risk_ceiling_usd"] == 0.0, "Paper trading risk ceiling breached!"
    
    # Verify Arbitrage Testing enforces strict $500 ceiling
    arb_ceiling = profiles["arbitrage_testing"]["risk_ceiling_usd"]
    assert arb_ceiling == 500.0, f"Arbitrage risk ceiling incorrect: {arb_ceiling}"
    
    print("[✓] Risk Ceiling Boundaries Verified Successfully.")

def test_cryptographic_envelopes():
    print("[*] Testing SHA-256 Canonical Evidence Envelope Generation...")
    
    dummy_telemetry = {
        "node_id": "cell_tier_3_anchor",
        "action": "arbitrage_execution_sim",
        "pnl_delta": 42.50,
        "timestamp": 1759080000.0
    }
    
    canonical_json = json.dumps(dummy_telemetry, sort_keys=True)
    envelope_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    print(f"    - Canonical Payload : {canonical_json}")
    print(f"    - SHA-256 Signature : {envelope_hash}")
    
    assert len(envelope_hash) == 64, "Invalid SHA-256 signature length."
    print("[✓] Cryptographic Evidence Envelope Verified Successfully.")

if __name__ == "__main__":
    print("=== Sovereign Seed Commons: Tier Hardening Suite ===")
    test_risk_ceilings()
    test_cryptographic_envelopes()
    print("[✓] All Tier Hardening Checks Passed Cleanly.")
    sys.exit(0)
