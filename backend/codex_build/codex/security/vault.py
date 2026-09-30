"""
Local Vault module for secure key custody using the OS Keyring.

Provides a unified interface to store and retrieve encryption keys securely
via Windows Credential Manager, macOS Keychain, or Linux Secret Service,
with a safe fallback mechanism for headless / Docker environments.
"""

import os
import base64
import logging
from typing import Optional, Dict

import keyring
from keyring.errors import KeyringError

from .crypto_field import AES_256_KEY_SIZE, generate_key, CryptoError

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = "project_codex"


class VaultError(CryptoError):
    """Raised when an operation on the Local Vault fails."""
    pass


class LocalVault:
    """
    Manages local cryptographic keys using OS Credential Storage.
    """

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME):
        self.service_name = service_name
        self._memory_fallback: Dict[str, bytes] = {}
        self._keyring_available = self._test_keyring()

    def _test_keyring(self) -> bool:
        """Check if OS keyring backend is accessible in the current environment."""
        try:
            test_val = keyring.get_password(self.service_name, "__codex_vault_probe__")
            return True
        except Exception as e:
            logger.warning(
                "OS Keyring not available or headless environment detected: %s. Using safe fallback.",
                e
            )
            return False

    def get_key(self, key_name: str) -> Optional[bytes]:
        """
        Retrieve a symmetric key from the vault.

        Args:
            key_name: Unique identifier for the key (e.g., 'db_encryption_key').

        Returns:
            The raw 32-byte key, or None if not found.
        """
        # 1. Check environment variable override (e.g. CI/CD or Docker container)
        env_var_name = f"CODEX_KEY_{key_name.upper().replace('-', '_')}"
        if env_var_name in os.environ:
            try:
                return base64.urlsafe_b64decode(os.environ[env_var_name])
            except Exception:
                pass

        # 2. Check in-memory store
        if key_name in self._memory_fallback:
            return self._memory_fallback[key_name]

        # 3. Retrieve from OS keyring
        if self._keyring_available:
            try:
                stored = keyring.get_password(self.service_name, key_name)
                if stored:
                    raw_key = base64.urlsafe_b64decode(stored)
                    if len(raw_key) == AES_256_KEY_SIZE:
                        return raw_key
            except Exception as e:
                logger.error("Failed to read key '%s' from OS keyring: %s", key_name, e)

        return None

    def set_key(self, key_name: str, key_bytes: bytes) -> None:
        """
        Store a symmetric key in the vault.

        Args:
            key_name: Unique identifier for the key.
            key_bytes: Exactly 32 bytes of cryptographic key material.
        """
        if not isinstance(key_bytes, (bytes, bytearray)) or len(key_bytes) != AES_256_KEY_SIZE:
            raise ValueError(f"Key must be exactly {AES_256_KEY_SIZE} bytes.")

        encoded_key = base64.urlsafe_b64encode(key_bytes).decode("ascii")

        if self._keyring_available:
            try:
                keyring.set_password(self.service_name, key_name, encoded_key)
                return
            except Exception as e:
                logger.warning("Failed to save to OS keyring (%s), saving to memory fallback.", e)
                self._keyring_available = False

        # Store in memory fallback if keyring is unavailable
        self._memory_fallback[key_name] = key_bytes

    def get_or_create_key(self, key_name: str) -> bytes:
        """
        Retrieve an existing key, or generate and store a new 256-bit key if absent.

        Args:
            key_name: Unique identifier for the key.

        Returns:
            A 32-byte cryptographic key.
        """
        existing = self.get_key(key_name)
        if existing:
            return existing

        new_key = generate_key()
        self.set_key(key_name, new_key)
        return new_key

    def delete_key(self, key_name: str) -> bool:
        """
        Delete a key from the vault.

        Args:
            key_name: Identifier of the key to remove.

        Returns:
            True if removed, False otherwise.
        """
        removed = False
        if key_name in self._memory_fallback:
            del self._memory_fallback[key_name]
            removed = True

        if self._keyring_available:
            try:
                keyring.delete_password(self.service_name, key_name)
                removed = True
            except KeyringError:
                pass
            except Exception as e:
                logger.error("Failed to delete key '%s' from OS keyring: %s", key_name, e)

        return removed


# Singleton instance for standard app usage
default_vault = LocalVault()
