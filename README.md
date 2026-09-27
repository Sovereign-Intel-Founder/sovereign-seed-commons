# Sovereign Seed Commons - Participant Cell

> **WARNING:** This is a small, local, offline-by-default participant bridge for the Sovereign Seed Commons. It is not the founder's private bare-metal Toll Bridge, does not access production infrastructure, does not submit financial transactions, and does not require private keys or specialized hardware.

## Purpose
This repository provides a small, safe, cloneable participant cell for local experimentation, offline validation, and pull-request contributions.

## Safety & Boundaries
- Binds strictly to `127.0.0.1` by default.
- Zero `shell=True` or arbitrary command execution.
- Strict operation allowlist and request limits.
- Offline-by-default execution producing bounded machine-readable evidence.
