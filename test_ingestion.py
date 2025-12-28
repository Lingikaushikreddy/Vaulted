import asyncio
import os
import json
from pathlib import Path
from aegis_core.database.connection import init_db, get_db
from aegis_core.database.models import StoredDocument
from aegis_core.crypto.security import AegisSecurity
from aegis_core.ingestion.handlers import IngestionManager

async def test_ingestion_flow():
    print("--- Starting Ingestion Integration Test ---")
    
    # 1. Setup paths
    base_path = Path("test_data_ingestion")
    base_path.mkdir(exist_ok=True)
    
    # Create a dummy CSV
    csv_file = base_path / "finance_data.csv"
    csv_content = "date,amount,category\n2024-01-01,100,Groceries\n2024-01-02,50,Transport"
    csv_file.write_text(csv_content)
    
    encrypted_file = base_path / "finance_data.enc"
    
    # 2. Ingest
    print("Ingesting CSV...")
    manager = IngestionManager()
    data = manager.ingest_file(csv_file)
    print(f"Ingested {data['metadata']['row_count']} rows.")
    
    # 3. Encrypt (We encrypt the ORIGINAL file for storage, or the extracted content? 
    # Architecture says: Store raw data encrypted. 
    # We might verify extraction for indexing, but store the file.)
    print("Encrypting Original File...")
    security = AegisSecurity(key_path="test_aegis.key")
    security.encrypt_file(csv_file, encrypted_file)
    
    # 4. Store Metadata + Extracted Info
    print("Saving to DB...")
    await init_db()
    async with get_db() as db:
        doc = StoredDocument(
            filename="finance_data.csv",
            file_path=str(encrypted_file),
            file_hash="hash_csv", 
            tags="finance,csv",
            meta_info=json.dumps(data['metadata']) # Storing extracted metadata
        )
        db.add(doc)
        await db.commit()
        print(f"Saved Document with Metadata: {doc.meta_info}")

    print("SUCCESS: Ingestion flow complete.")

if __name__ == "__main__":
    asyncio.run(test_ingestion_flow())
