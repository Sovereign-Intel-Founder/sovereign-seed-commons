# Sovereign Seed Commons - Bare-Metal Audit & Performance Evidence (2026)

## Overview
This directory contains offline, non-production, reproducible verification artifacts and performance telemetry gathered on bare-metal hardware.

## Classification of Artifacts
* **Functional Tests**: Validates component loading, basic socket initialization, and resilience handlers (`test_adapters.py`, `test_commons.py`, `test_loader.py`, `test_resilience.py`).
* **Integration Tests**: Internal component wiring and local loopback handling.
* **Benchmarks & Experiments**: Controlled synthetic queue boundary and saturation audits.
* **Unsupported Claims**: Any metrics or behaviors not explicitly measured via local offline instrumentation are excluded.

## Hardware Manifest
- Test Host: 128 cores, 728 GB RAM
- Architecture: AMD EPYC Bare-Metal Server
- Location: Ashburn, Virginia
- Environment: Debian/Linux
