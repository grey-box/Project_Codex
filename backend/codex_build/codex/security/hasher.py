"""
Module for secure password hashing using Argon2id.

Follows OWASP recommendations for password storage.
"""

from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# Default OWASP-aligned configuration for Argon2id
_DEFAULT_HASHER = PasswordHasher(
    time_cost=3,          # 3 iterations
    memory_cost=65536,    # 64 MB memory
    parallelism=4,        # 4 parallel threads
    hash_len=32,          # 32 bytes output hash
    salt_len=16           # 16 bytes random salt
)


def get_hasher() -> PasswordHasher:
    """Return the singleton instance of the default PasswordHasher."""
    return _DEFAULT_HASHER


def hash_password(plain_password: str, hasher: Optional[PasswordHasher] = None) -> str:
    """
    Hash a plain text password using Argon2id.

    Args:
        plain_password: The user's plain text password.
        hasher: Optional custom PasswordHasher instance.

    Returns:
        The encoded Argon2id hash string including salt and parameters.
    """
    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError("Password must be a non-empty string.")

    active_hasher = hasher or _DEFAULT_HASHER
    return active_hasher.hash(plain_password)


def verify_password(password_hash: str, plain_password: str, hasher: Optional[PasswordHasher] = None) -> bool:
    """
    Verify a plain text password against an Argon2id hash in constant time.

    Args:
        password_hash: The stored Argon2id hash string.
        plain_password: The candidate plain text password.
        hasher: Optional custom PasswordHasher instance.

    Returns:
        True if the password matches, False otherwise.
    """
    if not isinstance(password_hash, str) or not isinstance(plain_password, str):
        return False

    active_hasher = hasher or _DEFAULT_HASHER
    try:
        return active_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str, hasher: Optional[PasswordHasher] = None) -> bool:
    """
    Check if a stored hash needs to be recomputed due to updated hasher parameters.

    Args:
        password_hash: The stored Argon2id hash string.
        hasher: Optional custom PasswordHasher instance.

    Returns:
        True if the hash was created with older/different parameters.
    """
    if not isinstance(password_hash, str):
        return True

    active_hasher = hasher or _DEFAULT_HASHER
    try:
        return active_hasher.check_needs_rehash(password_hash)
    except Exception:
        return True
