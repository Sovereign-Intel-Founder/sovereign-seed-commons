#!/usr/bin/env bash
set -e

# Colors for elite presentation
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║          SOVEREIGN INTELLIGENCE PROTOCOL — SEED COMMONS           ║"
echo "║             Bare-Metal Mesh Participant Bootstrap v1.0              ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "[*] Running pre-flight system integrity checks..."
sleep 0.5

# Check Python & SQLite
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[✗] Critical: Python 3.x is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] Python 3.x runtime verified.${NC}"

# Check SQLite WAL support
python3 -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.execute('PRAGMA journal_mode=WAL;')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}[✗] Critical: SQLite WAL mode support missing.${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] SQLite Write-Ahead Logging (WAL) engine verified.${NC}"

echo -e "\n${YELLOW}[?] Select Your Participation Tier:${NC}"
echo "    1) Regular Commons      (Standard Health & Mesh Validation | \$0 Risk)"
echo "    2) Paper Trading        (Live-Shadow Simulation Mode       | \$0 Risk)"
echo "    3) Arbitrage Testing    (Live Sim / Latency Target <2.5ms  | \$500 Risk Ceiling)"
echo ""
read -p "Select tier [1-3]: " tier_choice

case $tier_choice in
    1)
        SELECTED_TIER="regular_commons"
        ;;
    2)
        SELECTED_TIER="paper_trading"
        ;;
    3)
        SELECTED_TIER="arbitrage_testing"
        ;;
    *)
        echo -e "${RED}[✗] Invalid selection. Aborting deployment.${NC}"
        exit 1
        ;;
esac

echo -e "\n${CYAN}[*] Initializing Cell Mutation for: ${SELECTED_TIER^^}...${NC}"
sleep 0.5

# Run the cell runner script
python3 scripts/cell_runner.py --tier "$SELECTED_TIER"

echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║             CELL DEPLOYMENT & HARDENING SUCCESSFUL                ║"
echo "║       Node is securely tethered to the Sovereign Mesh Ledger.     ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
