import os
import keyring
import base64
import secrets
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SERVICE_NAME = "vaulted_core"
USERNAME = "vault_master_key_v2"

class VaultSecurity:
    def __init__(self, key_path: str = "vault_key.key", use_keyring: bool = True):
        self.key_path = Path(key_path)
        self.use_keyring = use_keyring
        self.key = self._load_or_generate_key()
        self.aesgcm = AESGCM(self.key)

    def _load_or_generate_key(self) -> bytes:
        # 1. Try Keyring first
        if self.use_keyring:
            try:
                stored_key = keyring.get_password(SERVICE_NAME, USERNAME)
                if stored_key:
                    return base64.urlsafe_b64decode(stored_key)
            except Exception:
                pass

        # 2. Try File (Fallback)
        if self.key_path.exists():
            try:
                # Try reading as base64 (Jules' format)
                return base64.urlsafe_b64decode(self.key_path.read_bytes())
            except Exception:
                # Fallback to raw bytes (Legacy format)
                return self.key_path.read_bytes()
        
        # 3. Generate New (AES-256 = 32 bytes)
        return self._rotate_key()

    def _rotate_key(self) -> bytes:
        """Generates a new 256-bit key and saves it."""
        key = AESGCM.generate_key(bit_length=256)
        key_b64 = base64.urlsafe_b64encode(key)
        
        # Save to Keyring
        if self.use_keyring:
            try:
                keyring.set_password(SERVICE_NAME, USERNAME, key_b64.decode('utf-8'))
            except Exception as e:
                # In production logs, this should be a warning
                pass

        # Save to File (Backup)
        self.key_path.write_bytes(key_b64)
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass
            
        return key

    def rotate_master_key(self, reencrypt_files: list[Path] = None):
        """
        Public method to trigger rotation.
        DANGER: If reencrypt_files is not provided, old data may become unreadable
        unless the old key is archived (which this implementation currently does not do).

        Enhancement: Supports immediate re-encryption of critical files.
        """
        old_aesgcm = self.aesgcm

        print("Rotating Master Key...")
        self.key = self._rotate_key()
        self.aesgcm = AESGCM(self.key)

        if reencrypt_files:
            print(f"Re-encrypting {len(reencrypt_files)} files...")
            for fpath in reencrypt_files:
                if fpath.exists():
                    try:
                        # Decrypt with OLD key
                        with open(fpath, "rb") as f:
                            enc_data = f.read()

                        # Validate Format
                        if len(enc_data) < 28:
                             continue

                        nonce = enc_data[:12]
                        ciphertext = enc_data[12:]
                        plaintext = old_aesgcm.decrypt(nonce, ciphertext, None)

                        # Encrypt with NEW key
                        new_enc_data = self.encrypt_data(plaintext)
                        with open(fpath, "wb") as f:
                            f.write(new_enc_data)

                        print(f"Re-encrypted: {fpath}")
                    except Exception as e:
                        print(f"Failed to re-encrypt {fpath}: {e}")

    def encrypt_data(self, data: bytes) -> bytes:
        """Format: [NONCE (12 bytes)][CIPHERTEXT + TAG]"""
        nonce = secrets.token_bytes(12)
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_data(self, token: bytes) -> bytes:
        if len(token) < 28:
            raise ValueError("Token too short")
        nonce = token[:12]
        ciphertext = token[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)

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
