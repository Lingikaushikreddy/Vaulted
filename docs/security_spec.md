# AEGIS - Security Specification

**Role**: Senior Security Architect
**Date**: 2025-12-27
**Status**: APPROVED

---

## 1. Cryptographic Standards

### 1.1 Data at Rest (The Aegis)
*   **Algorithm**: AES-256-GCM (Galois/Counter Mode).
*   **Justification**: Provides both confidentiality and integrity (AEAD). CBC mode is rejected due to lack of built-in integrity and padding oracle risks.
*   **Implementation**: `cryptography.fernet` (Note: Fernet uses AES-128-CBC with HMAC-SHA256 by default. To meet "AES-256" strict enterprise requirements, we may need to migrate to `ChaCha20-Poly1305` or a custom AES-256-GCM wrapper if Fernet is insufficient. *Current Audited State: Fernet is secure, but we label it AES-128*).
    *   *Correction*: Fernet uses 128-bit AES. For the "Senior Architect" role, we must upgrade this to **AES-256-GCM** via `cryptography.hazmat` if 256-bit is a hard requirement.

### 1.2 Data in Transit
*   **Protocol**: TLS 1.3 only.
*   **Cipher Suites**: `TLS_AES_256_GCM_SHA384` or `TLS_CHACHA20_POLY1305_SHA256`.
*   **Authentication**: mTLS (Mutual TLS) for Gateway <-> Enterprise communication.

---

## 2. Key Lifecycle Management (KMS)

### 2.1 Storage
*   **Root Key**: Stored in Hardware-backed OS Keystore.
    *   macOS: **Keychain** (Secure Enclave).
    *   Windows: **DPAPI** / Credential Locker.
    *   Linux: **Secret Service API** (GNOME Keyring / KWallet).
*   **Fallback**: Encrypted Keyfile (AES-256-GCM) protected by user passphrase (rejecting plain keyfiles).

### 2.2 Rotation Policy
*   **Trigger**:
    *   Time-based (Every 90 days).
    *   Event-based (Device compromise suspicion).
*   **Mechanism**:
    1.  Generate new `Key_V2`.
    2.  Decrypt `Master_Key_V1` -> Re-encrypt with `Key_V2` (Envelope Encryption).
    3.  *Or for Data Keys*: Decrypt all data with `Key_V1` and re-encrypt with `Key_V2`. (Expensive but necessary for total compromise recovery).

---

## 3. Secure Aggregation & Zero Trust

### 3.1 FL Trust Model
The Server is **Honest-but-Curious**. It follows the protocol but tries to learn inputs.
*   **Mitigation**: **Secure Aggregation (SecAgg)**.
    *   Clients add random masks to their updates: $W_i + Mask_i$.
    *   Server sums updates: $\sum (W_i + Mask_i) = \sum W_i + \sum Mask_i$.
    *   Masks are designed to sum to zero ($\sum Mask_i = 0$) ONLY if sufficient clients participate.
    *   Result: Server sees aggregate, but never individual $W_i$.

## 4. Threat Mitigation Playbooks

### Scenario A: Lost Device
1.  **Detection**: Heartbeat failure or user report.
2.  **Action**: 
    *   Revoke Client ID Certification revocation list (CRL).
    *   Since data is encrypted at rest, physical theft does not yield data without the Keychain passphrase.

### Scenario B: Rogue Server (Poisoning)
1.  **Detection**: Accuracy metrics drop on validation set.
2.  **Action**:
    *   Trigger "Audit Mode": Clients require explicit user approval for next 5 jobs.
    *   Verify Job Signatures against Backup Registry.

---

## 5. Security Audit Report (Current)
*   **Finding 01**: `cryptography.fernet` defaults to 128-bit AES.
    *   *Remediation*: Upgrade to `cryptography.hazmat.primitives.ciphers.aead.AESGCM` for true 256-bit security.
*   **Finding 02**: Key Rotation is not currently implemented.
    *   *Remediation*: Implement `rotate_key()` method immediately.
