import os
import ssl
from pathlib import Path
import sys

def check_permissions(path: Path, expected: str):
    """Check file permissions (Linux/Unix only)."""
    if not path.exists():
        print(f"[MISSING] {path}")
        return

    st = os.stat(path)
    oct_perm = oct(st.st_mode)[-3:]
    if oct_perm == expected:
        print(f"[PASS] {path} permissions are {oct_perm}")
    else:
        print(f"[FAIL] {path} permissions are {oct_perm} (expected {expected})")

def check_tls_config(cert_path: Path):
    if not cert_path.exists():
        print(f"[FAIL] TLS Cert missing at {cert_path}")
        return

    try:
        cert_data = cert_path.read_bytes()
        print(f"[PASS] TLS Cert found ({len(cert_data)} bytes)")
    except Exception as e:
        print(f"[FAIL] Could not read TLS Cert: {e}")

def main():
    print("=== VAULTED Security Audit ===")

    # 1. Check Key Permissions
    key_file = Path("vault_key.key")
    if key_file.exists():
        check_permissions(key_file, "600")
    else:
        print("[INFO] No local key file found (checking keyring instead?)")

    # 2. Check Certs
    certs_dir = Path("certs")
    check_tls_config(certs_dir / "cert.pem")
    check_permissions(certs_dir / "key.pem", "600")

    # 3. Check Dependencies (Basic)
    try:
        import cryptography
        print(f"[PASS] Cryptography library present (v{cryptography.__version__})")
    except ImportError:
        print("[FAIL] Cryptography library missing!")

    print("\nAudit Complete.")

if __name__ == "__main__":
    main()
