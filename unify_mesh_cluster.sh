#!/bin/bash
set -e

echo "================================================================="
echo " SOVEREIGN INTELLIGENCE PROTOCOL - UNIFIED MESH ORCHESTRATOR"
echo "================================================================="

# Step 1: Terminate all redundant processes, python loops, and conflicting daemons
echo "[1/4] Purging redundant background loops and freeing ports..."
sudo systemctl stop sip-commons.service || true
pkill -f start_commons_daemon.py || true
pkill -f sip_gossip.py || true
sudo fuser -k 9999/udp || true

# Step 2: Enforce canonical bootstrap IP in the native source
echo "[2/4] Hardcoding canonical master seed (216.22.11.194)..."
sed -i 's/#define GLOBAL_BOOTSTRAP_HOST ".*"/#define GLOBAL_BOOTSTRAP_HOST "216.22.11.194"/' sovereign_gossip.c

# Step 3: Compile the high-performance C11 transport engine with native optimizations
echo "[3/4] Compiling unified C11 bare-metal core..."
gcc -O3 -march=native sovereign_gossip.c -o sip_gossip_native -lcrypto -lrt

# Step 4: Configure and start the permanent systemd service daemon
echo "[4/4] Deploying unified systemd mesh service..."
sudo tee /etc/systemd/system/sip-commons.service > /dev/null << 'SERVICE'
[Unit]
Description=Sovereign Intelligence Protocol - Unified Bare-Metal Mesh Core
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/joshua445s12590275/sovereign_workspace/sovereign-seed-commons
ExecStart=/home/joshua445s12590275/sovereign_workspace/sovereign-seed-commons/sip_gossip_native 9999
Restart=always
RestartSec=2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable sip-commons.service
sudo systemctl restart sip-commons.service

echo "================================================================="
echo " UNIFIED MESH ACTIVE. Streaming live telemetry and node traffic:"
echo "================================================================="
sudo journalctl -u sip-commons.service -f -o cat
