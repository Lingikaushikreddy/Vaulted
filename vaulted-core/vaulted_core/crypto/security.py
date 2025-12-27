import os
import keyring
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pathlib import Path

SERVICE_NAME = "vaulted_core"
USERNAME = "vault_master_key"

class VaultSecurity:
    def __init__(self, key_path: str = "vault_key.key", use_keyring: bool = True):
        self.key_path = Path(key_path)
        self.use_keyring = use_keyring
        self.key = self._load_or_generate_key()
        self.aesgcm = AESGCM(self.key)

    def _load_or_generate_key(self) -> bytes:
        # AES-256 requires 32-byte key
        key = None
        
        # 1. Try Keyring
        if self.use_keyring:
            stored_key = keyring.get_password(SERVICE_NAME, USERNAME)
            if stored_key:
                try:
                    key = base64.urlsafe_b64decode(stored_key)
                except:
                    pass

        # 2. Try File
        if not key and self.key_path.exists():
            key = self.key_path.read_bytes()
        
        # 3. Validation
        if key and len(key) == 32:
            return key
            
        print("Existing key invalid or missing. Generating new AES-256 key.")
        return self._rotate_key()

    def _rotate_key(self) -> bytes:
        """Generates a new 256-bit key and saves it."""
        key = AESGCM.generate_key(bit_length=256) # 32 bytes
        
        # Save to Keyring
        if self.use_keyring:
            try:
                keyring.set_password(SERVICE_NAME, USERNAME, base64.urlsafe_b64encode(key).decode('utf-8'))
                print("New AES-256 Key saved to OS Keychain.")
            except Exception as e:
                print(f"Keyring failed ({e}).")

        # Save to File (Backup)
        self.key_path.write_bytes(key)
        os.chmod(self.key_path, 0o600)
        return key

    def encrypt_data(self, data: bytes) -> bytes:
        # AES-GCM requires a nonce (IV). We generate a unique one per encryption.
        nonce = os.urandom(12) 
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_data(self, token: bytes) -> bytes:
        # Extract nonce (first 12 bytes)
        nonce = token[:12]
        ciphertext = token[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)

    def rotate_master_key(self):
        """
        Public method to trigger key rotation. 
        REAL WORLD NOTE: This simply replaces the master key for NEW encryptions.
        Old data would need to be re-encrypted. This is a partial implementation.
        """
        print("Rotating Master Key...")
        self.key = self._rotate_key()
        self.aesgcm = AESGCM(self.key)

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
