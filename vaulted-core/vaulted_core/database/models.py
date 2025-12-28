from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class StoredDocument(Base):
    """Represents a file stored in the vault."""
    __tablename__ = "stored_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String, unique=True) # Path to the encrypted file on disk
    file_hash = Column(String) # For integrity checking
    tags = Column(String) # Comma-separated tags
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata extracted from the file (JSON string)
    meta_info = Column(Text, default="{}") 

class AuditLog(Base):
    """Logs every access to the vault (Immutable Ledger)."""
    __tablename__ = "audit_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor_id = Column(String)       # Who requested it?
    action_type = Column(String)    # LOGIN, TRAIN_REQUEST, DATA_INGEST
    target_resource = Column(String)# File hash or Job ID
    verdict = Column(String)        # ALLOWED / DENIED
    policy_id = Column(Integer, nullable=True) # Which consent policy justified this?
    
    # Extra details (JSON)
    details = Column(Text, default="{}")

    # Structured compliance check results (JSON)
    # e.g. {"checks": [{"rule": "GDPR_CONSENT", "passed": true}]}
    compliance_check_details = Column(Text, default="{}")

class ConsentPolicy(Base):
    """Defines rules for data usage."""
    __tablename__ = "consent_policies"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(String)      # e.g., "did:web:healthcorp.com" or "user_me"
    name = Column(String)
    description = Column(String)
    allowed_actions = Column(String) # e.g., "TRAIN_MODEL", "STATISTICS"
    target_tags = Column(String)    # e.g., "health, finance"
    expiry = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)

    # Compliance & Minimization
    # JSON map: {"GDPR": ["Art.6(1)(a)"], "HIPAA": ["§164.502"]}
    regulation_mapping = Column(Text, default="{}")
    # JSON rules: {"allowed_columns": ["age", "diagnosis"], "row_filter": "age > 18"}
    data_minimization_rules = Column(Text, default="{}")
