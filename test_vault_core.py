import asyncio
import os
from pathlib import Path
from vaulted_core.database.connection import init_db, get_db
from vaulted_core.database.models import StoredDocument
from vaulted_core.crypto.security import VaultSecurity
from sqlalchemy import select

async def test_vault_flow():
    print("--- Starting Vault Core Test ---")
    
    # 1. Setup paths
    base_path = Path("test_data")
    import shutil
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(exist_ok=True)
    
    # Cleanup DB if exists
    if os.path.exists("vault.db"):
        os.remove("vault.db")
    
    input_file = base_path / "secret.txt"
    input_file.write_text("This is my highly sensitive medical record.")
    
    encrypted_file = base_path / "secret.enc"
    decrypted_file = base_path / "secret_decrypted.txt"
    
    # 2. Initialize Infrastructure
    print("Initializing Database...")
    await init_db()
    
    security = VaultSecurity(key_path="test_vault.key")
    print(f"Encryption Key Generated at: {security.key_path}")

    # 3. Simulate "Ingestion"
    print("Encrypting file...")
    security.encrypt_file(input_file, encrypted_file)
    
    # 4. Store Metadata
    print("Saving metadata to DB...")
    async with get_db() as db:
        doc = StoredDocument(
            filename="secret.txt",
            file_path=str(encrypted_file),
            file_hash="dummy_hash_123", # In real app we'd calc sha256
            tags="medical,sensitive"
        )
        db.add(doc)
        await db.commit()
        doc_id = doc.id
        print(f"Document saved with ID: {doc_id}")

    # 5. Retrieve & Decrypt
    print("Retrieving and Decrypting...")
    async with get_db() as db:
        result = await db.execute(select(StoredDocument).where(StoredDocument.id == doc_id))
        retrieved_doc = result.scalar_one()
        
        print(f"Found document: {retrieved_doc.filename} (Path: {retrieved_doc.file_path})")
        
        security.decrypt_file(Path(retrieved_doc.file_path), decrypted_file)
        
    # 6. Verify Content
    original_content = input_file.read_text()
    decrypted_content = decrypted_file.read_text()
    
    if original_content == decrypted_content:
        print("SUCCESS: Decrypted content matches original!")
    else:
        print("FAILURE: Content mismatch!")
        print(f"Original: {original_content}")
        print(f"Decrypted: {decrypted_content}")

    # Cleanup
    # os.remove("vault.db")
    # os.remove("test_vault.key")
    # import shutil
    # shutil.rmtree("test_data")

if __name__ == "__main__":
    asyncio.run(test_vault_flow())
