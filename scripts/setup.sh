#!/usr/bin/env bash
set -e
echo "=== Setting up Sovereign Seed Commons ==="
python3 -m venv .venv 2>/dev/null
source .venv/bin/activate 2>/dev/null
pip install --upgrade pip 2>/dev/null
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
echo "Setup complete."
