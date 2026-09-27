#!/usr/bin/env bash
export SOVEREIGN_SECRET="${SOVEREIGN_SECRET:-local-test-secret}"
exec python3 tools/cell_runner.py run
