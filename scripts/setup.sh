#!/usr/bin/env bash
set -euo pipefail
echo "Initializing Sovereign Seed Commons local environment..."
python3 -m venv venv || true
source venv/bin/activate || true
pip install --upgrade pip
echo "Setup complete. Run ./scripts/test.sh to execute local smoke tests."
