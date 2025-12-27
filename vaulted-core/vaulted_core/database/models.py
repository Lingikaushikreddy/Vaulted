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

class AccessLog(Base):
    """Logs every access to the vault."""
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor_id = Column(String) # Who accessed it (User user_id or FL Server ID)
    action = Column(String) # READ, WRITE, TRAIN
    resource_id = Column(Integer) # ID of the StoredDocument (if applicable)
    status = Column(String) # SUCCESS, DENIED

class ConsentPolicy(Base):
    """Defines rules for data usage."""
    __tablename__ = "consent_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    allowed_actions = Column(String) # e.g., "TRAIN, READ_METADATA" - Comma separated for MVP
    target_data_tags = Column(String) # e.g., "health, finance" (applies to docs with these tags)
    revoked = Column(Boolean, default=False)
