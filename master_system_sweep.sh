#!/bin/bash
set -e

echo "================================================================="
echo " SOVEREIGN INTELLIGENCE PROTOCOL - GLOBAL ENVIRONMENT SWEEP"
echo "================================================================="

# Step 1: Discover all related components across workspace directories
echo "[1/4] Scanning environments for active nodes, toll bridges, and configs..."
find . -type f \( -name "*.c" -name "*.py" -o -name "*.sh" -o -name "*.json" \) | grep -v "\.git"

# Step 2: Ensure correct permissions and clean socket/shared memory bindings
echo "[2/4] Validating POSIX shared memory paths and permissions..."
if [ ! -d "/dev/shm" ]; then
    mkdir -p /dev/shm
fi
touch /dev/shm/sip_mesh_shm
chmod 666 /dev/shm/sip_mesh_shm

# Step 3: Re-verify compilation with zero-copy and cryptographic linking
echo "[3/4] Rebuilding native core with full hardware telemetry support..."
gcc -O3 -march=native sovereign_gossip.c -o sip_gossip_native -lcrypto -lrt

# Step 4: Ensure systemd service is active, clean, and monitoring
echo "[4/4] Finalizing systemd service binding..."
sudo systemctl daemon-reload
sudo systemctl restart sip-commons.service

echo "================================================================="
echo " MASTER SWEEP COMPLETE. System is fully integrated and live:"
echo "================================================================="
sudo journalctl -u sip-commons.service -n 20 --no-pager
