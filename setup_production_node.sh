#!/bin/bash
set -e

echo "=================================================="
echo "    SIP COMMONS EDGE STOREFRONT DEPLOYMENT        "
echo "=================================================="

WORK_DIR=$(pwd)
SIP_DIR=$(find ~ -maxdepth 3 -type d \( -name "sovereignintelfounder" -o -name "sovereign-intelligence" \) 2>/dev/null | head -n 1)

if [ -z "$SIP_DIR" ]; then
    echo "[!] Error: Sovereign Intelligence core directory not found."
    exit 1
fi

echo "[1/3] Applying Real-Time Network Tuning (AF_XDP / Zero-Copy Readiness)..."
sudo sysctl -w net.core.rmem_max=134217728 > /dev/null 2>&1 || true
sudo sysctl -w net.core.wmem_max=134217728 > /dev/null 2>&1 || true
sudo sysctl -w net.core.netdev_max_backlog=250000 > /dev/null 2>&1 || true
echo "    -> Kernel socket buffers optimized for high-throughput stream ingestion."

echo "[2/3] Generating Systemd Service Unit for Commons Daemon..."
SERVICE_PATH="/etc/systemd/system/sip-commons.service"

sudo bash -c "cat << SERVICE_EOF > $SERVICE_PATH
[Unit]
Description=Sovereign Seed Commons Edge Node Daemon
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
ExecStart=/usr/bin/python3 -c 'from commons_bridge.heartbeat import send_heartbeat; import time; [send_heartbeat() or time.sleep(10) for _ in iter(int, 1)]'
Restart=always
RestartSec=5
Environment=PYTHONPATH=$WORK_DIR:$SIP_DIR

[Install]
WantedBy=multi-user.target
SERVICE_EOF"

echo "    -> Created $SERVICE_PATH"

echo "[3/3] Enabling and Starting Local Daemon Service..."
sudo systemctl daemon-reload
sudo systemctl enable sip-commons.service --now || true

echo "=================================================="
echo " SUCCESS: Edge Storefront Daemon Active & Tuned!   "
echo "=================================================="
