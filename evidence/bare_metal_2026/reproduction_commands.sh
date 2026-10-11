#!/usr/bin/env bash
set -euo pipefail

# Functional Tests
./build/venv/bin/python test_adapters.py
./build/venv/bin/python test_commons.py
./build/venv/bin/python test_loader.py
./build/venv/bin/python test_resilience.py

# Benchmark EXP-01: SPSC Ring Buffer Saturation / Throughput
gcc -O3 -Wall -Wextra -pthread -I./include -I./sovereign_seed_commons/include scripts/sip_spsc_ring.c -o /tmp/sip_spsc_ring
/tmp/sip_spsc_ring
