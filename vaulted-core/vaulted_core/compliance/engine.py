from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.models import ConsentPolicy, AuditLog

class ComplianceEngine:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def check_consent(self, entity_id: str, action: str, tags: List[str]) -> bool:
        """
        Checks if a valid, non-expired, non-revoked policy exists for the requested action on the given tags.
        """
        # 1. Fetch active policies for this entity
        stmt = select(ConsentPolicy).where(
            ConsentPolicy.entity_id == entity_id,
            ConsentPolicy.revoked == False
        )
        result = await self.db.execute(stmt)
        policies = result.scalars().all()

        # 2. Filter match
        allowed = False
        justifying_policy_id = None

        for policy in policies:
            # Check expiration
            if policy.expiry and policy.expiry < datetime.utcnow():
                continue
            
            # Check Action
            if action not in policy.allowed_actions.split(","):
                continue

            # Check Tags (Simple intersection logic)
            policy_tags = set(policy.target_tags.split(","))
            requested_tags = set(tags)
            
            if requested_tags.issubset(policy_tags):
                allowed = True
                justifying_policy_id = policy.id
                break
        
        # 3. Audit Log
        await self.log_access(
            actor_id=entity_id,
            action_type=action,
            target_resource=f"tags:{','.join(tags)}",
            verdict="ALLOWED" if allowed else "DENIED",
            policy_id=justifying_policy_id
        )

        return allowed

    async def log_access(self, actor_id: str, action_type: str, target_resource: str, verdict: str, policy_id: Optional[int] = None):
        """Writes to the immutable audit log."""
        log_entry = AuditLog(
            actor_id=actor_id,
            action_type=action_type,
            target_resource=target_resource,
            verdict=verdict,
            policy_id=policy_id,
            timestamp=datetime.utcnow()
        )
        self.db.add(log_entry)
        await self.db.commit()
