import os
import keyring
import base64
from cryptography.fernet import Fernet
from pathlib import Path

SERVICE_NAME = "vaulted_core"
USERNAME = "vault_master_key"

class VaultSecurity:
    def __init__(self, key_path: str = "vault_key.key", use_keyring: bool = True):
        self.key_path = Path(key_path)
        self.use_keyring = use_keyring
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        # 1. Try Keyring first
        if self.use_keyring:
            stored_key = keyring.get_password(SERVICE_NAME, USERNAME)
            if stored_key:
                return base64.urlsafe_b64decode(stored_key)

        # 2. Try File (Fallback)
        if self.key_path.exists():
            return self.key_path.read_bytes()
        
        # 3. Generate New
        key = Fernet.generate_key()
        
        # 4. Save
        if self.use_keyring:
            try:
                # Keyring stores strings, so encode bytes to b64 string
                keyring.set_password(SERVICE_NAME, USERNAME, base64.urlsafe_b64encode(key).decode('utf-8'))
                print("Key saved to OS Keychain.")
                return key
            except Exception as e:
                print(f"Keyring failed ({e}), falling back to file.")
        
        # Fallback to file
        self.key_path.write_bytes(key)
        os.chmod(self.key_path, 0o600)
        return key

    def encrypt_data(self, data: bytes) -> bytes:
        return self.cipher.encrypt(data)

    def decrypt_data(self, token: bytes) -> bytes:
        return self.cipher.decrypt(token)

    def encrypt_file(self, file_path: Path, output_path: Path):
        with open(file_path, "rb") as f:
            data = f.read()
        
        encrypted_data = self.encrypt_data(data)
        
        with open(output_path, "wb") as f:
            f.write(encrypted_data)

    def decrypt_file(self, encrypted_path: Path, output_path: Path):
        with open(encrypted_path, "rb") as f:
            data = f.read()
        
        decrypted_data = self.decrypt_data(data)
        
        with open(output_path, "wb") as f:
            f.write(decrypted_data)
