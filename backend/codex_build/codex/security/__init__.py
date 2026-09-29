"""
Security and Cryptography Utilities for Project Codex.

Provides:
- Argon2id password hashing and constant-time verification.
- AES-256-GCM authenticated field encryption (reversible strings).
- AES-256-GCM chunked streaming file encryption/decryption.
- Local Vault key custody using OS Keyring.
"""

from .hasher import hash_password, verify_password, needs_rehash
from .crypto_field import (
    generate_key,
    encrypt_field,
    decrypt_field,
    CryptoError,
    DecryptionError,
    AES_256_KEY_SIZE
)
from .crypto_file import encrypt_file, decrypt_file
from .vault import LocalVault, default_vault, VaultError

__all__ = [
    # Password hashing (Argon2id)
    "hash_password",
    "verify_password",
    "needs_rehash",
    # Field encryption (AES-256-GCM)
    "generate_key",
    "encrypt_field",
    "decrypt_field",
    "CryptoError",
    "DecryptionError",
    "AES_256_KEY_SIZE",
    # File encryption (AES-256-GCM streaming)
    "encrypt_file",
    "decrypt_file",
    # Local Vault (OS Keyring)
    "LocalVault",
    "default_vault",
    "VaultError",
]
