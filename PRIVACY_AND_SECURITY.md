# Privacy and Security Policy: Sovereign Intelligence Protocol (SIP)

As a decentralized, GitHub-native execution mesh operating across diverse edge devices and user hardware, SIP enforces strict privacy and security guarantees by design.

## 1. Ephemeral State & Automatic Wiping
* **Stateless Execution:** All tasks executed within a cell must run in isolated, temporary environments.
* **Immediate Purging:** Once a task completes and the signed `evidence_return.json` proof is generated, all local input payloads, intermediate variables, and temporary workspace files are instantly wiped from storage. No execution data is retained.

## 2. Data Minimization & PII Prohibition
* **No Plaintext PII:** The protocol strictly prohibits transmitting or storing raw, unencrypted Personally Identifiable Information (PII) across the mesh.
* **Cryptographic Commitments:** Input data must be hashed, anonymized, or tokenized before entering the task execution loop. Cells process abstract workloads, not user identities.

## 3. Strict Workload Sandboxing
* **Host Isolation:** Cell runtimes must enforce rigorous sandboxing (such as containerization or microVM isolation). 
* **Zero Host Access:** Code executed inside a cell has zero access to the host device's file system, local credentials, or unrelated system processes.

## 4. Compliance by Design
* By enforcing local-first execution, cryptographic evidence verification over raw data exposure, and absolute storage limitation, SIP provides a privacy-preserving framework aligned with global data protection standards (including GDPR and CCPA principles).
