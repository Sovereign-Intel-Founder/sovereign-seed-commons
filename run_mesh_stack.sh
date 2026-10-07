#!/bin/bash
cd ~/sovereign_workspace/sovereign-seed-commons
echo "[STACK] Starting Sovereign Intelligence Protocol automated execution stack..."

while true; do
    ./sip_persister
    sleep 5
done
