# GDPR / Regulatory Mapping

This document outlines how the VAULTED system's technical controls map to regulatory requirements (GDPR, CCPA, HIPAA).

## GDPR Mapping

### Article 6: Lawfulness of Processing
* **Requirement**: Processing is lawful only if at least one of the conditions applies (e.g., Consent).
* **Implementation**:
    * `ConsentPolicy` model stores explicit consent rules.
    * `ComplianceEngine` enforces these rules before any data access (`check_consent`).
    * The `regulation_mapping` field in policies explicitly links them to "GDPR Art.6".

### Article 17: Right to Erasure ('Right to be Forgotten')
* **Requirement**: The data subject has the right to obtain from the controller the erasure of personal data.
* **Implementation**:
    * `KeyShredder` class in `vaulted_core/compliance/shredder.py` implements crypto-shredding.
    * By destroying the encryption key, data becomes mathematically inaccessible, effectively erasing it.

### Article 25: Data Protection by Design and by Default
* **Requirement**: Implement appropriate technical and organizational measures (e.g., pseudonymisation, minimisation).
* **Implementation**:
    * **Data Minimization**: `ComplianceEngine.enforce_minimization()` filters data to return only necessary columns defined in the policy.
    * **Encryption**: All data is stored encrypted at rest (AES-256-GCM).

### Article 30: Records of Processing Activities
* **Requirement**: Maintain a record of processing activities.
* **Implementation**:
    * `AuditLog` records every access attempt (actor, action, resource, verdict).
    * `compliance_check_details` field stores specific regulation checks performed.

## CCPA Mapping

### Right to Opt-Out
* **Implementation**: `ConsentPolicy.revoked` field allows immediate revocation of consent, blocking future access.

## HIPAA Mapping

### § 164.312(b) Audit Controls
* **Requirement**: Implement hardware, software, and/or procedural mechanisms that record and examine activity in information systems.
* **Implementation**: Immutable `AuditLog` tracks all access to PHI (Protected Health Information).

### § 164.312(c)(1) Integrity
* **Requirement**: Protect electronic protected health information from improper alteration or destruction.
* **Implementation**:
    * `StoredDocument.file_hash` ensures data integrity.
    * AES-GCM provides authenticated encryption (detects tampering).
