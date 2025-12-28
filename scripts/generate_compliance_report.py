import asyncio
import json
import os
from sqlalchemy import select
from vaulted_core.database.connection import get_db, init_db
from vaulted_core.database.models import ConsentPolicy, AuditLog

async def generate_report():
    print("Generating Compliance Dashboard...")
    if not os.path.exists("vault.db"):
        print("Error: vault.db not found. Run tests or ingest data first.")
        return

    async with get_db() as db:
        # 1. Policies Stats
        res = await db.execute(select(ConsentPolicy))
        policies = res.scalars().all()

        active_policies = [p for p in policies if not p.revoked]
        gdpr_policies = [p for p in policies if "GDPR" in p.regulation_mapping]

        print("\n--- CONSENT POLICY COVERAGE ---")
        print(f"Total Policies: {len(policies)}")
        print(f"Active Policies: {len(active_policies)}")
        print(f"GDPR-Mapped Policies: {len(gdpr_policies)}")

        # 2. Audit Logs Stats
        res = await db.execute(select(AuditLog))
        logs = res.scalars().all()

        allowed_count = len([l for l in logs if l.verdict == "ALLOWED"])
        denied_count = len([l for l in logs if l.verdict == "DENIED"])

        print("\n--- AUDIT TRAIL SUMMARY ---")
        print(f"Total Access Attempts: {len(logs)}")
        print(f"Access Allowed: {allowed_count}")
        print(f"Access Denied: {denied_count}")

        print("\n--- RECENT VIOLATIONS ---")
        denials = [l for l in logs if l.verdict == "DENIED"][-5:]
        if not denials:
            print("No recent violations found.")
        for d in denials:
            print(f"- [{d.timestamp}] {d.actor_id} attempted {d.action_type} on {d.target_resource}")

        # 3. Generate Markdown Report
        report_content = f"""# Compliance Dashboard
Generated on: {asyncio.get_event_loop().time()}

## Consent Policy Coverage
- **Total Policies**: {len(policies)}
- **Active Policies**: {len(active_policies)}
- **GDPR-Mapped Policies**: {len(gdpr_policies)}

## Audit Trail Summary
- **Total Access Attempts**: {len(logs)}
- **Access Allowed**: {allowed_count}
- **Access Denied**: {denied_count}

## Recent Violations
"""
        for d in denials:
            report_content += f"- [{d.timestamp}] {d.actor_id} attempted {d.action_type} on {d.target_resource}\n"

        with open("COMPLIANCE_DASHBOARD.md", "w") as f:
            f.write(report_content)
        print("\nReport saved to COMPLIANCE_DASHBOARD.md")

if __name__ == "__main__":
    asyncio.run(generate_report())
