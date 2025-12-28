# AEGIS Encryption Specification

## Overview
This document outlines the cryptographic standards and implementations used within the AEGIS ecosystem to ensure Confidentiality, Integrity, and Key Safety.

## 1. Encryption-at-Rest (Local Data)
All sensitive data stored locally on client devices (e.g., training data, model checkpoints) is encrypted using **AES-256-GCM**.

*   **Algorithm**: AES-256-GCM (Galois/Counter Mode).
*   **Key Size**: 256-bit (32 bytes).
*   **Nonce Size**: 96-bit (12 bytes), randomly generated per encryption operation.
*   **Implementation**: `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
*   **Format**: `[NONCE (12 bytes)] || [CIPHERTEXT] || [TAG (16 bytes, included in ciphertext by library)]`.

### Key Management
*   **Storage**:
    1.  **Primary**: OS System Keyring (via `keyring` library). Service: `aegis_core`, Username: `aegis_master_key_v2`.
    2.  **Fallback**: Local file `aegis_key.key` (Base64 encoded).
*   **Permissions**: Fallback file is restricted to `0600` (Read/Write owner only).
*   **Rotation**: Keys can be rotated. *Note: Historic data re-encryption is currently manual.*

## 2. Encryption-in-Transit (Network)
All network communication between the Gateway, Server, and Clients is secured using **TLS 1.3**.

*   **Gateway**: FastAPI/Uvicorn configured with SSL/TLS context.
*   **FL Server**: Flower gRPC server secured with SSL credentials.
*   **Authentication**: Mutual TLS (mTLS) is recommended for production; currently token-based/TLS-terminated.

## 3. Secure Aggregation
To prevent the central server from inspecting individual model updates, AEGIS utilizes **Secure Aggregation**.

*   **Protocol**: Flower's implementation of Secure Aggregation (based on Bonawitz et al.).
*   **Guarantee**: The server can only see the sum of the model updates, not individual contributions.

## 4. Secure Enclave / TEE
*   **Status**: Roadmap.
*   **Integration**: Future versions will deploy the Aggregation Server inside an SGX/AMD-SEV enclave to guarantee code integrity and prevent memory inspection.
