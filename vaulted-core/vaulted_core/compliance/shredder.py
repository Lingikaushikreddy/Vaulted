import os
import keyring
from pathlib import Path
from ..crypto.security import SERVICE_NAME, USERNAME

class KeyShredder:
    """
    Implements the 'Right-to-Forget' by cryptographically erasing keys.
    """
    
    @staticmethod
    def shred_master_key(key_path: str = "vault_key.key"):
        print("!!! INITIATING CRYPTO-SHREDDING SEQUENCE !!!")
        
        # 1. Shred File Key (if exists)
        path = Path(key_path)
        if path.exists():
            # Pass 1: Random Noise
            size = path.stat().st_size
            path.write_bytes(os.urandom(size))
            # Pass 2: Zeros
            path.write_bytes(b'\x00' * size)
            # Pass 3: Delete
            os.remove(path)
            print("File key shredded.")

        # 2. Shred Keyring Entry
        try:
            # Overwrite with garbage before deleting? Keyring API doesn't guarantee overwrite logic, 
            # but setting random password first is good practice.
            keyring.set_password(SERVICE_NAME, USERNAME, "SHREDDED_GARBAGE_" + os.urandom(16).hex())
            keyring.delete_password(SERVICE_NAME, USERNAME)
            print("Keyring entry deleted.")
        except Exception as e:
            print(f"Keyring shredding warning: {e}")

        print("Master Key Destroyed. Data is now cryptographically inaccessible.")
