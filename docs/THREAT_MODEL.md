# VAULTED Threat Model & Mitigation Playbook

## 1. Asset Identification
*   **User Data**: Raw training data on edge devices. (Highest Sensitivity)
*   **Model Weights**: Global and local model parameters. (High Sensitivity)
*   **Cryptographic Keys**: Master encryption keys. (Critical)
*   **Infrastructure**: Gateway and Aggregation Server.

## 2. Threat Scenarios

### T1: Malicious Aggregation Server
*   **Description**: The central server tries to reconstruct user data from model updates (Inference Attacks) or inspect individual weights.
*   **Mitigation**:
    *   **Secure Aggregation**: Ensure server only sees aggregated updates.
    *   **Differential Privacy**: Add noise to updates (future work).
    *   **TEE**: Run aggregator in Enclave.

### T2: Device Theft / Physical Access
*   **Description**: Attacker gains physical access to a client device.
*   **Mitigation**:
    *   **Encryption-at-Rest**: Data is AES-256-GCM encrypted.
    *   **Key Protection**: Keys stored in OS Keyring or protected file (0600).

### T3: Man-in-the-Middle (MitM)
*   **Description**: Attacker intercepts network traffic.
*   **Mitigation**:
    *   **TLS 1.3**: Strictly enforced for all connections.
    *   **Certificate Pinning**: (Recommended for client apps).

### T4: Rogue Client (Poisoning)
*   **Description**: A malicious client submits bad updates to ruin the global model.
*   **Mitigation**:
    *   **Robust Aggregation**: Use median-based aggregation (e.g., Krum, Trimmed Mean) instead of FedAvg.
    *   **Authentication**: Strict Client ID checks.

## 3. Incident Response Playbook

### Key Compromise
1.  **Revoke**: If a client key is stolen, revoke client access at Gateway.
2.  **Rotate**: Trigger `VaultSecurity.rotate_master_key()` on affected device.
3.  **Re-encrypt**: Re-process local data with new key.

### Data Leak
1.  **Isolate**: Disconnect affected nodes.
2.  **Audit**: Check logs for unauthorized access.
3.  **Patch**: Update encryption specs or firewall rules.
