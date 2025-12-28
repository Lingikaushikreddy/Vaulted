import asyncio
import os
from pathlib import Path
from aegis_core.database.connection import init_db, get_db
import json
from aegis_core.database.models import ConsentPolicy, AuditLog
from aegis_core.compliance.engine import ComplianceEngine
from sqlalchemy import select

async def test_compliance():
    print("--- Starting Compliance Integration Test ---")
    
    # Cleanup DB to force schema update
    if os.path.exists("aegis-core/aegis.db"):
        os.remove("aegis-core/aegis.db")
    if os.path.exists("aegis.db"):
        os.remove("aegis.db")
        
    # 1. Init DB
    await init_db()
    
    async with get_db() as db:
        # 2. Setup Policy with Minimization & GDPR
        print("Creating Consent Policy with Minimization & GDPR...")
        policy = ConsentPolicy(
            entity_id="health_corp",
            name="Medical Training",
            description="Allow training on med data",
            allowed_actions="TRAIN_MODEL",
            target_tags="medical",
            revoked=False,
            regulation_mapping=json.dumps({"GDPR": ["Art.6(1)(a)"]}),
            data_minimization_rules=json.dumps({"allowed_columns": ["diagnosis", "age"]})
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

        # 4. Test Minimization
        print("Testing Data Minimization...")
        mock_data = [
            {"name": "Alice", "age": 30, "diagnosis": "Flu", "ssn": "123-45"},
            {"name": "Bob", "age": 25, "diagnosis": "Cold", "ssn": "678-90"}
        ]
        minimized = engine.enforce_minimization(mock_data, policy)
        print(f"Original keys: {mock_data[0].keys()}")
        print(f"Minimized keys: {minimized[0].keys()}")

        assert "ssn" not in minimized[0], "SSN should be removed"
        assert "name" not in minimized[0], "Name should be removed"
        assert "diagnosis" in minimized[0], "Diagnosis should remain"
        print("Minimization: SUCCESS")

        # 5. Test Check (Denied - Wrong Tag)
        print("Checking DENIED request (Wrong Tag)...")
        denied_tag = await engine.check_consent(
            entity_id="health_corp", 
            action="TRAIN_MODEL", 
            tags=["finance"]
        )
        assert denied_tag == False, "Should be DENIED"
        print("Verdict: DENIED (Correct)")
        
        # 6. Verify Audit Logs & Details
        print("Verifying Audit Logs...")
        result = await db.execute(select(AuditLog))
        logs = result.scalars().all()
        print(f"Total Logs: {len(logs)}")
        for log in logs:
            print(f"- [{log.timestamp}] {log.actor_id} -> {log.action_type}: {log.verdict}")
            if log.verdict == "ALLOWED":
                 details = json.loads(log.compliance_check_details)
                 print(f"  Compliance Details: {details}")
                 assert "regulations" in details
                 assert "GDPR" in details["regulations"]

        assert len(logs) >= 2

    print("SUCCESS: Compliance flow complete.")

if __name__ == "__main__":
    asyncio.run(test_compliance())
