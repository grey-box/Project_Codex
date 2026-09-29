"""
Module for field-level authenticated encryption using AES-256-GCM.

Provides reversible encryption for sensitive fields, API tokens, and credentials.
"""

import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

# Standard AES-256 key size in bytes
AES_256_KEY_SIZE = 32
# Recommended standard GCM nonce size in bytes
GCM_NONCE_SIZE = 12


class CryptoError(Exception):
    """Base exception for cryptographic operations."""
    pass


class DecryptionError(CryptoError):
    """Raised when decryption fails due to invalid key, corruption, or tampering."""
    pass


def generate_key() -> bytes:
    """Generate a cryptographically secure 256-bit (32-byte) symmetric key."""
    return AESGCM.generate_key(bit_length=256)


def encrypt_field(plaintext: str, key: bytes, associated_data: Optional[bytes] = None) -> str:
    """
    Encrypt a plaintext string using AES-256-GCM.

    Args:
        plaintext: The string to encrypt.
        key: A 32-byte (256-bit) encryption key.
        associated_data: Optional non-secret data bound to authentication tag.

    Returns:
        A URL-safe Base64-encoded string containing [12-byte Nonce + Ciphertext + 16-byte Tag].
    """
    if not isinstance(plaintext, str):
        raise ValueError("Plaintext must be a string.")
    if not isinstance(key, (bytes, bytearray)) or len(key) != AES_256_KEY_SIZE:
        raise ValueError(f"Encryption key must be exactly {AES_256_KEY_SIZE} bytes.")

    nonce = os.urandom(GCM_NONCE_SIZE)
    aesgcm = AESGCM(key)
    
    # AESGCM.encrypt returns ciphertext + tag
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data)
    
    # Combined payload: nonce + ciphertext + tag
    payload = nonce + ciphertext_and_tag
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt_field(encoded_payload: str, key: bytes, associated_data: Optional[bytes] = None) -> str:
    """
    Decrypt and verify a Base64-encoded ciphertext payload using AES-256-GCM.

    Args:
        encoded_payload: The Base64 string produced by encrypt_field.
        key: The 32-byte (256-bit) encryption key.
        associated_data: Optional non-secret data that was bound during encryption.

    Returns:
        The decrypted plaintext string.

    Raises:
        DecryptionError: If the key is invalid, or payload was tampered with or corrupted.
    """
    if not isinstance(encoded_payload, str) or not encoded_payload.strip():
        raise ValueError("Encoded payload must be a non-empty string.")
    if not isinstance(key, (bytes, bytearray)) or len(key) != AES_256_KEY_SIZE:
        raise ValueError(f"Encryption key must be exactly {AES_256_KEY_SIZE} bytes.")

    try:
        payload = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
    except Exception as e:
        raise DecryptionError("Failed to decode base64 payload.") from e

    if len(payload) < GCM_NONCE_SIZE + 16:  # Nonce + min 16-byte tag
        raise DecryptionError("Payload is too short to be a valid AES-GCM ciphertext.")

    nonce = payload[:GCM_NONCE_SIZE]
    ciphertext_and_tag = payload[GCM_NONCE_SIZE:]

    aesgcm = AESGCM(key)
    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data)
        return decrypted_bytes.decode("utf-8")
    except InvalidTag as e:
        raise DecryptionError(
            "Authentication failed: data has been tampered with or incorrect key provided."
        ) from e
    except UnicodeDecodeError as e:
        raise DecryptionError("Decrypted data is not valid UTF-8 text.") from e
