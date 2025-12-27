import os
import unittest
import shutil
from pathlib import Path
from vaulted_core.crypto.security import VaultSecurity
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class TestVaultSecurity(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_crypto_tmp")
        self.test_dir.mkdir(exist_ok=True)
        self.key_path = self.test_dir / "test.key"

        # Ensure clean state
        if self.key_path.exists():
            os.remove(self.key_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_key_generation_and_storage(self):
        # Initialize security (should generate key)
        # Force no keyring to test file fallback
        sec = VaultSecurity(key_path=str(self.key_path), use_keyring=False)

        self.assertTrue(self.key_path.exists())
        self.assertEqual(len(sec.key), 32) # AES-256

        # Re-initialize (should load key)
        sec2 = VaultSecurity(key_path=str(self.key_path), use_keyring=False)
        self.assertEqual(sec.key, sec2.key)

    def test_encryption_decryption(self):
        sec = VaultSecurity(key_path=str(self.key_path), use_keyring=False)
        data = b"Hello, World! This is a secret."

        encrypted = sec.encrypt_data(data)

        # Check structure: 12 bytes nonce + ciphertext + 16 bytes tag
        self.assertTrue(len(encrypted) == 12 + len(data) + 16)

        decrypted = sec.decrypt_data(encrypted)
        self.assertEqual(data, decrypted)

    def test_file_encryption(self):
        sec = VaultSecurity(key_path=str(self.key_path), use_keyring=False)
        input_file = self.test_dir / "input.txt"
        enc_file = self.test_dir / "enc.bin"
        output_file = self.test_dir / "output.txt"

        data = b"File encryption test content."
        input_file.write_bytes(data)

        sec.encrypt_file(input_file, enc_file)
        self.assertTrue(enc_file.exists())
        self.assertNotEqual(enc_file.read_bytes(), data)

        sec.decrypt_file(enc_file, output_file)
        self.assertEqual(output_file.read_bytes(), data)

    def test_tampered_data(self):
        sec = VaultSecurity(key_path=str(self.key_path), use_keyring=False)
        data = b"Vital Data"
        encrypted = bytearray(sec.encrypt_data(data))

        # Tamper with the last byte
        encrypted[-1] ^= 0x01

        with self.assertRaises(Exception):
            sec.decrypt_data(bytes(encrypted))

if __name__ == '__main__':
    unittest.main()
