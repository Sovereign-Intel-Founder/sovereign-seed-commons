# Security Model

The project already contains a substantial layered security model. The cleanup is consolidating, documenting, and removing legacy ambiguity—not building security from scratch.

## Core Mechanisms
- **Ed25519 Canonical Signatures**: Enforced across cell validation and task manifests.
- **Constant-Time Verification**: Prevents side-channel timing attacks during signature checks.
- **State Resurrection & Integrity**: Verified state recovery protocols.
