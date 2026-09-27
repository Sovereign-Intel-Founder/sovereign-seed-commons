# Contributing to Sovereign Seed Commons

The Sovereign Seed Commons operates under strict architectural sovereignty. Contributions are evaluated deterministically by machine-readable evidence manifests and cryptographic validation. Human review occurs only after automated gates pass.

## Contributor Lifecycle for External Cells

1. **Fork & Initialize:**
   Fork the repository to your local environment and sync with `origin/main`.

2. **Run Local Validation:**
   Before submitting any mutation or code change, run the evidence manifest validator to ensure structural compliance:
   ```bash
   python3 tools/validate_evidence.py
