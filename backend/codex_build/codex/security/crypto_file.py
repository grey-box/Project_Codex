"""
Module for authenticated file encryption and decryption using AES-256-GCM.

Supports chunked streaming to handle large database files (dumps, SQLite)
with constant low memory footprint and tamper detection.
"""

import os
import struct
from pathlib import Path
from typing import Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from .crypto_field import AES_256_KEY_SIZE, GCM_NONCE_SIZE, DecryptionError

FILE_MAGIC_HEADER = b"CODEX_AESGCM_V1"
CHUNK_SIZE = 64 * 1024  # 64 KB chunks
TAG_SIZE = 16


def encrypt_file(
    source_path: Union[str, Path],
    dest_path: Union[str, Path],
    key: bytes,
    chunk_size: int = CHUNK_SIZE
) -> None:
    """
    Encrypt a file using AES-256-GCM in streaming chunks.

    Args:
        source_path: Path to the unencrypted source file.
        dest_path: Path where encrypted file will be created.
        key: A 32-byte (256-bit) encryption key.
        chunk_size: Byte size of each chunk to stream (default 64 KB).

    Raises:
        FileNotFoundError: If source_path does not exist.
        ValueError: If key length is invalid.
    """
    source = Path(source_path)
    dest = Path(dest_path)

    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")
    if not isinstance(key, (bytes, bytearray)) or len(key) != AES_256_KEY_SIZE:
        raise ValueError(f"Encryption key must be exactly {AES_256_KEY_SIZE} bytes.")

    aesgcm = AESGCM(key)
    file_size = source.stat().st_size

    # Ensure parent directory for destination exists
    dest.parent.mkdir(parents=True, exist_ok=True)

    with open(source, "rb") as fin, open(dest, "wb") as fout:
        # Write format identifier
        fout.write(FILE_MAGIC_HEADER)
        fout.write(struct.pack(">I", chunk_size))

        chunk_idx = 0
        bytes_read = 0

        while True:
            data = fin.read(chunk_size)
            bytes_read += len(data)
            is_last = (bytes_read >= file_size) or (len(data) == 0)

            nonce = os.urandom(GCM_NONCE_SIZE)
            # Associated data binds chunk index and last-chunk flag to prevent reordering/truncation
            associated_data = struct.pack(">IB", chunk_idx, 1 if is_last else 0)

            encrypted_chunk = aesgcm.encrypt(nonce, data, associated_data)

            # Record format: [length 4 bytes] + [is_last 1 byte] + [nonce 12 bytes] + [ciphertext + tag]
            fout.write(struct.pack(">IB", len(encrypted_chunk), 1 if is_last else 0))
            fout.write(nonce)
            fout.write(encrypted_chunk)

            if is_last:
                break
            chunk_idx += 1


def decrypt_file(
    source_path: Union[str, Path],
    dest_path: Union[str, Path],
    key: bytes
) -> None:
    """
    Decrypt and authenticate a file encrypted by encrypt_file.

    Args:
        source_path: Path to the encrypted file.
        dest_path: Path where the decrypted plaintext file will be written.
        key: The 32-byte (256-bit) encryption key.

    Raises:
        FileNotFoundError: If source_path does not exist.
        DecryptionError: If file is corrupted, tampered with, truncated, or key is wrong.
    """
    source = Path(source_path)
    dest = Path(dest_path)

    if not source.is_file():
        raise FileNotFoundError(f"Encrypted source file not found: {source}")
    if not isinstance(key, (bytes, bytearray)) or len(key) != AES_256_KEY_SIZE:
        raise ValueError(f"Encryption key must be exactly {AES_256_KEY_SIZE} bytes.")

    aesgcm = AESGCM(key)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Use a temporary file for writing during decryption to prevent leaving corrupted files
    temp_dest = dest.with_suffix(dest.suffix + ".tmp_decrypt")

    try:
        with open(source, "rb") as fin, open(temp_dest, "wb") as fout:
            # Check magic header
            magic = fin.read(len(FILE_MAGIC_HEADER))
            if magic != FILE_MAGIC_HEADER:
                raise DecryptionError("Invalid file header: not a Codex encrypted file.")

            # Read chunk size configured during encryption
            chunk_size_bytes = fin.read(4)
            if len(chunk_size_bytes) < 4:
                raise DecryptionError("Truncated header in encrypted file.")

            chunk_idx = 0
            completed_cleanly = False

            while True:
                chunk_meta = fin.read(5)
                if not chunk_meta:
                    break

                if len(chunk_meta) < 5:
                    raise DecryptionError("Truncated chunk metadata encountered.")

                chunk_len, is_last_byte = struct.unpack(">IB", chunk_meta)
                is_last = (is_last_byte == 1)

                nonce = fin.read(GCM_NONCE_SIZE)
                if len(nonce) < GCM_NONCE_SIZE:
                    raise DecryptionError("Truncated nonce in encrypted chunk.")

                encrypted_chunk = fin.read(chunk_len)
                if len(encrypted_chunk) < chunk_len:
                    raise DecryptionError("Truncated chunk data encountered.")

                associated_data = struct.pack(">IB", chunk_idx, is_last_byte)

                try:
                    decrypted_chunk = aesgcm.decrypt(nonce, encrypted_chunk, associated_data)
                except InvalidTag as e:
                    raise DecryptionError(
                        f"Integrity check failed at chunk {chunk_idx}: file tampered or wrong key."
                    ) from e

                fout.write(decrypted_chunk)

                if is_last:
                    completed_cleanly = True
                    break
                chunk_idx += 1

            if not completed_cleanly:
                raise DecryptionError("File ended unexpectedly without final chunk marker.")

        # Atomic rename to final target path
        if dest.exists():
            dest.unlink()
        temp_dest.rename(dest)

    except Exception:
        if temp_dest.exists():
            temp_dest.unlink()
        raise
