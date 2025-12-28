# AEGIS TEE Integration Roadmap

## Overview
This document outlines the strategy for migrating the Aggregation Server to a Trusted Execution Environment (TEE) to mitigate Threat T1 (Malicious Aggregation Server).

## Target Architecture
*   **Hardware**: Intel SGX (Software Guard Extensions) or AMD SEV-SNP.
*   **Framework**: Gramine (formerly Graphene) or SCONE.

## Integration Steps

### Phase 1: Containerization (Current)
*   Ensure `aegis-server` runs cleanly in a Docker container.
*   Minimize dependencies to reduce the Trusted Computing Base (TCB).

### Phase 2: Gramine Manifest
*   Create `aegis-server.manifest.template`.
*   Define allowed files (certs, python scripts) and network sockets.
*   **Goal**: Run the Python server inside Gramine-SGX.

### Phase 3: Remote Attestation
*   Implement an Attestation Service.
*   **Workflow**:
    1.  Client challenges Server.
    2.  Server produces SGX Quote (signed by hardware key).
    3.  Client verifies Quote with Intel Attestation Service (IAS).
    4.  Client establishes TLS connection *only* if quote is valid.

### Phase 4: Secret Provisioning
*   The TLS private key should be generated *inside* the enclave or provisioned securely via a Secret Management Service (SMS) post-attestation.
