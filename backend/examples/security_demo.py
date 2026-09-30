"""
Security Module Example / Demo
Project Codex — Grey-Box

Usage:
    python backend/examples/security_demo.py
"""

import sys
from pathlib import Path

# Ensure backend/codex_build is in sys.path so imports work from any working directory
backend_dir = Path(__file__).resolve().parent.parent / "codex_build"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

from codex.security import (  # type: ignore
    hash_password,
    verify_password,
    generate_key,
    encrypt_field,
    decrypt_field,
    encrypt_file,
    decrypt_file,
    default_vault
)


def main():
    print("=" * 65)
    print("🛡️  SECURITY MODULE DEMO (PROJECT CODEX)")
    print("=" * 65)

    # 1. Password Hashing with Argon2id
    print("\n1️⃣  PASSWORD HASHING (Argon2id)")
    password = "SuperSecurePassword!2026"
    hashed = hash_password(password)
    print(f"👉 Plaintext password  : {password}")
    print(f"👉 Stored database hash: {hashed[:35]}... (total length: {len(hashed)})")
    print(f"👉 Matches correctly?  : {verify_password(hashed, password)}")
    print(f"👉 Rejects wrong pwd?  : {not verify_password(hashed, 'wrong_candidate_password')}")

    # 2. Field-Level Encryption with AES-256-GCM
    print("\n2️⃣  FIELD-LEVEL ENCRYPTION (AES-256-GCM)")
    secret_key = generate_key()
    sensitive_data = "sk_live_private_api_key_drugbank_987654"
    ciphertext = encrypt_field(sensitive_data, secret_key)
    decrypted_text = decrypt_field(ciphertext, secret_key)
    print(f"👉 Original plaintext  : {sensitive_data}")
    print(f"👉 Encrypted ciphertext: {ciphertext}")
    print(f"👉 Decrypted plaintext : {decrypted_text}")
    print(f"👉 Exact match?        : {sensitive_data == decrypted_text}")

    # 3. File-Level Encryption (Streaming 64KB Chunks)
    print("\n3️⃣  FILE-LEVEL ENCRYPTION (Streaming 64KB Chunks)")
    test_src = Path("test_original.txt")
    test_enc = Path("test_encrypted.enc")
    test_dec = Path("test_restored.txt")

    test_src.write_text("Confidential medical catalogue or local user database dump.", encoding="utf-8")
    encrypt_file(test_src, test_enc, secret_key)
    decrypt_file(test_enc, test_dec, secret_key)

    print(f"👉 Original file created : {test_src.name} ({test_src.stat().st_size} bytes)")
    print(f"👉 Encrypted file on disk: {test_enc.name} ({test_enc.stat().st_size} bytes)")
    print(f"👉 Restored file content : '{test_dec.read_text(encoding='utf-8')}'")

    # Clean up temporary test files
    for f in [test_src, test_enc, test_dec]:
        if f.exists():
            f.unlink()

    # 4. Local Vault (OS Keyring custody)
    print("\n4️⃣  LOCAL VAULT (OS Keyring Storage & Memory Fallback)")
    vault_key_name = "demo_encryption_key"
    stored_key = default_vault.get_or_create_key(vault_key_name)
    retrieved_key = default_vault.get_key(vault_key_name)
    print(f"👉 Key created/stored in Vault: {stored_key.hex()[:16]}... (32 bytes)")
    print(f"👉 Retrieved successfully?    : {stored_key == retrieved_key}")

    print("\n" + "=" * 65)
    print("✅ ALL SECURITY CHECKS COMPLETED SUCCESSFULLY")
    print("=" * 65)


if __name__ == "__main__":
    main()
