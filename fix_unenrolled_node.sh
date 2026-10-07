#!/usr/bin/env bash
set -e

echo "==> 1. Halting systemd restart loop..."
sudo systemctl stop sip-commons.service

WORKSPACE="$HOME/sovereign_workspace/sovereign-seed-commons"
cd "$WORKSPACE"

echo "==> 2. Backing up and clearing stale local identity..."
mkdir -p ./state_backup
TIMESTAMP=$(date +%s)
mv identity.json ./state_backup/identity_${TIMESTAMP}.json 2>/dev/null || true
mv node_state.json ./state_backup/node_state_${TIMESTAMP}.json 2>/dev/null || true
rm -f ~/.sip_identity.json 2>/dev/null || true

echo "==> 3. Running interactive re-enrollment / bootstrap..."
# Force identity re-bind or fresh token generation
python3 -c "
import sys
try:
    from sovereign_commons.identity import rebind_node, enroll_node
    print('Executing identity rebind...')
    rebind_node()
except Exception as e:
    print(f'Bootstrap step output: {e}')
"

echo "==> 4. Starting sip-commons service..."
sudo systemctl start sip-commons.service

echo "==> 5. Monitoring live service status..."
sleep 2
sudo journalctl -u sip-commons.service -n 15 --no-pager
