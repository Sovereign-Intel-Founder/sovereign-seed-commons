#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "Running evidence validation..."
python3 tools/validate_evidence.py

echo "Running tool unit tests..."
python3 -m unittest discover -s tools -p 'test_*.py' -v

echo "Running integration tests..."
python3 tools/integration_test.py

echo "Compiling Python source files..."
python3 -m compileall -q -f .

echo "All tests passed successfully!"
