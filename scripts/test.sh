#!/usr/bin/env bash
set -e
echo "=== Testing Sovereign Seed Commons ==="
source .venv/bin/activate 2>/dev/null
python3 -m unittest discover -s tests -p "*_test.py" 2>/dev/null
python3 commons_bridge/bridge.py --test 2>/dev/null
echo "Tests complete."
