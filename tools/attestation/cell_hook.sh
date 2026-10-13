#!/usr/bin/env bash
set -e
echo "Executing Sovereign Commons cell runner state attestation..."
python3 tools/attestation/hasher.py
echo "Evidence manifest successfully compiled and locked."
