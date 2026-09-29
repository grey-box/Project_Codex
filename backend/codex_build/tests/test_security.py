"""
Unit tests for the Codex Security and Cryptography Module.
"""

import os
import tempfile
import pytest
from pathlib import Path

from codex.security import (
    hash_password,
    verify_password,
    needs_rehash,
    generate_key,
    encrypt_field,
    decrypt_field,
    encrypt_file,
    decrypt_file,
    DecryptionError,
    LocalVault,
    AES_256_KEY_SIZE
)


class TestPasswordHasher:
    def test_hash_and_verify_success(self):
        password = "CorrectHorseBatteryStaple!2026"
        hashed = hash_password(password)

        assert hashed.startswith("$argon2id$")
        assert verify_password(hashed, password) is True

    def test_verify_failure_with_wrong_password(self):
        password = "SecureAdminPassword"
        hashed = hash_password(password)

        assert verify_password(hashed, "WrongPassword") is False
        assert verify_password(hashed, "") is False

    def test_unique_salts_for_identical_passwords(self):
        password = "IdenticalPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(hash1, password) is True
        assert verify_password(hash2, password) is True

    def test_empty_password_raises_error(self):
        with pytest.raises(ValueError):
            hash_password("")


class TestFieldEncryption:
    def test_encrypt_and_decrypt_success(self):
        key = generate_key()
        secret = "sk_live_very_secret_api_key_drugbank_999"

        encrypted = encrypt_field(secret, key)
        assert encrypted != secret

        decrypted = decrypt_field(encrypted, key)
        assert decrypted == secret

    def test_decrypt_with_wrong_key_fails(self):
        key1 = generate_key()
        key2 = generate_key()
        secret = "confidential_org_secret"

        encrypted = encrypt_field(secret, key1)
        with pytest.raises(DecryptionError):
            decrypt_field(encrypted, key2)

    def test_tampered_ciphertext_fails(self):
        key = generate_key()
        secret = "tamper_detection_test"
        encrypted = encrypt_field(secret, key)

        # Alter a character in the base64 payload
        tampered = encrypted[:-2] + ("A" if encrypted[-2] != "A" else "B") + encrypted[-1:]
        with pytest.raises(DecryptionError):
            decrypt_field(tampered, key)

    def test_associated_data_binding(self):
        key = generate_key()
        secret = "bound_secret"
        ad = b"user_id_42"

        encrypted = encrypt_field(secret, key, associated_data=ad)

        # Decrypt with matching AD succeeds
        assert decrypt_field(encrypted, key, associated_data=ad) == secret

        # Decrypt with mismatching AD fails
        with pytest.raises(DecryptionError):
            decrypt_field(encrypted, key, associated_data=b"user_id_99")


class TestFileEncryption:
    def test_file_encrypt_and_decrypt_roundtrip(self, tmp_path):
        key = generate_key()

        # Create a sample file larger than one 64KB chunk (e.g. 150 KB)
        src_file = tmp_path / "original_database.bin"
        enc_file = tmp_path / "encrypted_database.enc"
        dec_file = tmp_path / "restored_database.bin"

        test_data = os.urandom(150 * 1024)
        src_file.write_bytes(test_data)

        # Encrypt
        encrypt_file(src_file, enc_file, key)
        assert enc_file.exists()
        assert enc_file.stat().st_size > src_file.stat().st_size

        # Decrypt
        decrypt_file(enc_file, dec_file, key)
        assert dec_file.exists()
        assert dec_file.read_bytes() == test_data

    def test_file_tamper_detection(self, tmp_path):
        key = generate_key()

        src_file = tmp_path / "data.txt"
        enc_file = tmp_path / "data.enc"
        dec_file = tmp_path / "data_dec.txt"

        src_file.write_bytes(b"Important medical catalogue definitions.")
        encrypt_file(src_file, enc_file, key)

        # Tamper with the encrypted file (flip bytes in the middle)
        enc_data = bytearray(enc_file.read_bytes())
        enc_data[len(enc_data) - 5] ^= 0xFF
        enc_file.write_bytes(bytes(enc_data))

        # Decryption must fail and not leave a corrupted restored file
        with pytest.raises(DecryptionError):
            decrypt_file(enc_file, dec_file, key)

        assert not dec_file.exists()


class TestLocalVault:
    def test_vault_generate_and_retrieve_key(self):
        vault = LocalVault(service_name="test_codex_vault")
        key_id = "test_unit_key"

        # Key should be generated and stored
        key = vault.get_or_create_key(key_id)
        assert isinstance(key, bytes)
        assert len(key) == AES_256_KEY_SIZE

        # Subsequent retrieval must return the identical key
        retrieved = vault.get_key(key_id)
        assert retrieved == key

        # Cleanup
        vault.delete_key(key_id)
