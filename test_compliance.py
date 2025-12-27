import asyncio
import os
from pathlib import Path
from vaulted_core.database.connection import init_db, get_db
from vaulted_core.database.models import ConsentPolicy, AuditLog
from vaulted_core.compliance.engine import ComplianceEngine
from sqlalchemy import select

async def test_compliance():
    print("--- Starting Compliance Integration Test ---")
    
    # Cleanup DB to force schema update
    if os.path.exists("vaulted-core/vault.db"):
        os.remove("vaulted-core/vault.db")
    if os.path.exists("vault.db"):
        os.remove("vault.db")
        
    # 1. Init DB
    await init_db()
    
    async with get_db() as db:
        # 2. Setup Policy
        print("Creating Consent Policy...")
        policy = ConsentPolicy(
            entity_id="health_corp",
            name="Medical Training",
            description="Allow training on med data",
            allowed_actions="TRAIN_MODEL",
            target_tags="medical",
            revoked=False
        )
        db.add(policy)
        await db.commit()
        
        # 3. Test Check (Allowed)
        engine = ComplianceEngine(db)
        print("Checking ALLOWED request...")
        allowed = await engine.check_consent(
            entity_id="health_corp", 
            action="TRAIN_MODEL", 
            tags=["medical"]
        )
        assert allowed == True, "Should be ALLOWED"
        print("Verdict: ALLOWED (Correct)")

        # 4. Test Check (Denied - Wrong Tag)
        print("Checking DENIED request (Wrong Tag)...")
        denied_tag = await engine.check_consent(
            entity_id="health_corp", 
            action="TRAIN_MODEL", 
            tags=["finance"]
        )
        assert denied_tag == False, "Should be DENIED"
        print("Verdict: DENIED (Correct)")
        
        # 5. Test Check (Denied - Wrong Entity)
        print("Checking DENIED request (Wrong Entity)...")
        denied_entity = await engine.check_consent(
            entity_id="random_hacker", 
            action="TRAIN_MODEL", 
            tags=["medical"]
        )
        assert denied_entity == False, "Should be DENIED"
        print("Verdict: DENIED (Correct)")

        # 6. Verify Audit Logs
        print("Verifying Audit Logs...")
        result = await db.execute(select(AuditLog))
        logs = result.scalars().all()
        print(f"Total Logs: {len(logs)}")
        for log in logs:
            print(f"- [{log.timestamp}] {log.actor_id} -> {log.action_type} on {log.target_resource}: {log.verdict}")
            
        assert len(logs) >= 3

    print("SUCCESS: Compliance flow complete.")

if __name__ == "__main__":
    asyncio.run(test_compliance())
