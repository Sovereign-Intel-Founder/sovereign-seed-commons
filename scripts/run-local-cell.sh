#!/usr/bin/env bash
set -e
echo "=== Launching Participant Cell (127.0.0.1:8999) ==="
source .venv/bin/activate 2>/dev/null
python3 commons_bridge/bridge.py
