#!/usr/bin/env bash
set -euo pipefail

# Permanently prevent Python from writing bytecode caches during test runs
export PYTHONDONTWRITEBYTECODE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Clean up any pre-existing cache directories just in case
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Running evidence validation..."
python3 tools/validate_evidence.py

echo "Running tool unit tests..."
python3 -m unittest discover -s tools -p 'test_*.py' -v

echo "Running integration tests..."
PYTHONPATH=. python3 tools/integration_test.py

echo "All tests passed successfully!"
