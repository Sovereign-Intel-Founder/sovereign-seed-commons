#!/usr/bin/env python3
import os
import subprocess
import sqlite3
import sys

GREEN = '\033[0;32m'
RED = '\033[0;31m'
NC = '\033[0m'

def log_status(name, success, details=""):
    if success:
        print(f"{GREEN}[✓] PASS: {name}{NC}")
    else:
        print(f"{RED}[✗] FAIL: {name}{NC}")
        if details:
            print(f"    └─> {details}")

def main():
    print(f"\n--- SOVEREIGN SEED COMMONS ENVIRONMENT VALIDATION ---\n")
    all_passed = True

    # 1. Verify File Permissions
    scripts = ["scripts/bootstrap_node.sh", "scripts/request_upgrade.sh", "scripts/strategy_template.py"]
    for s in scripts:
        if os.path.exists(s) and os.access(s, os.X_OK):
            log_status(f"Executable Permission: {s}", True)
        else:
            log_status(f"Executable Permission: {s}", False, "File missing or missing +x permission")
            all_passed = False

    # 2. Verify Database Ledger & WAL Mode
    db_path = "/tmp/sip_persistence_stress.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            if mode.lower() == "wal":
                log_status(f"SQLite WAL Persistence ({db_path})", True)
            else:
                log_status(f"SQLite WAL Persistence ({db_path})", False, f"Journal mode is {mode}, expected WAL")
                all_passed = False
            conn.close()
        except Exception as e:
            log_status("SQLite Database Access", False, str(e))
            all_passed = False
    else:
        log_status("SQLite Database Access", False, f"Ledger file not found at {db_path}")
        all_passed = False

    # 3. Test Tier Upgrade Handler
    res_up = subprocess.run(["./scripts/request_upgrade.sh", "paper_trading"], capture_output=True, text=True)
    if res_up.returncode == 0:
        log_status("Tier Elevation Routine (request_upgrade.sh paper_trading)", True)
    else:
        log_status("Tier Elevation Routine (request_upgrade.sh paper_trading)", False, res_up.stderr.strip())
        all_passed = False

    # 4. Test Strategy Simulation Harness Execution
    res_sim = subprocess.run([
        "./scripts/strategy_template.py",
        "--amount", "25.0",
        "--jito-tip", "0.002",
        "--max-slippage-bps", "30",
        "--latency-offset-ms", "8.0"
    ], capture_output=True, text=True)

    if res_sim.returncode == 0 and "SIP ARBITRAGE SIMULATION EXECUTION RETURN" in res_sim.stdout:
        log_status("Strategy Simulation Harness (strategy_template.py)", True)
    else:
        log_status("Strategy Simulation Harness (strategy_template.py)", False, res_sim.stderr.strip() or "Unexpected output")
        all_passed = False

    print("\n------------------------------------------------------")
    if all_passed:
        print(f"{GREEN}ALL COMMONS ENVIRONMENT CHECKS PASSED [✓]{NC}\n")
        sys.exit(0)
    else:
        print(f"{RED}ONE OR MORE CHECKS FAILED [✗]{NC}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
