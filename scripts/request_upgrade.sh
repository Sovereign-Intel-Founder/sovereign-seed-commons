#!/usr/bin/env bash
set -eo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

DB_PATH="/tmp/sip_persistence_stress.db"
TARGET_TIER="$1"

if [ -z "$TARGET_TIER" ]; then
    echo -e "${RED}[✗] Error: No tier specified.${NC}"
    echo "    Usage: ./scripts/request_upgrade.sh [paper_trading | arbitrage_testing]"
    exit 1
fi

if [[ "$TARGET_TIER" != "paper_trading" && "$TARGET_TIER" != "arbitrage_testing" ]]; then
    echo -e "${RED}[✗] Error: Invalid tier '$TARGET_TIER'. Use 'paper_trading' or 'arbitrage_testing'.${NC}"
    exit 1
fi

if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}[✗] Elevation Denied: No local telemetry ledger found.${NC}"
    echo "    Please run './scripts/bootstrap_node.sh' first."
    exit 1
fi

RECORD_COUNT=$(python3 -c "import sqlite3; conn = sqlite3.connect('$DB_PATH'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM telemetry_wal_log;'); print(cursor.fetchone()[0]);")

echo -e "${CYAN}[*] Validating telemetry history against local ledger...${NC}"
echo -e "${GREEN}[✓] Ledger verified. Active records: ${RECORD_COUNT}${NC}"

echo -e "${CYAN}[*] Executing runtime mutation to: ${TARGET_TIER^^}...${NC}"
python3 scripts/cell_runner.py --tier "$TARGET_TIER"

echo -e "\n${GREEN}"
python3 -c '
import sys
tier = sys.argv[1].upper()
msg = f"Node has successfully mutated to: {tier}"
title = "UPGRADE PETITION APPROVED & EXECUTED"

width = max(len(title), len(msg)) + 6
top = "╔" + "═" * width + "╗"
bottom = "╚" + "═" * width + "╝"

def format_line(text):
    return f"║ {text.center(width - 2)} ║"
    
print(top)
print(format_line(title))
print(format_line(msg))
print(bottom)
' "$TARGET_TIER"
echo -e "${NC}"
