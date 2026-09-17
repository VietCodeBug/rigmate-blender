"""Streaming file hash and metadata verification helpers."""

import hashlib
from pathlib import Path
from typing import Union

DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB chunks to prevent loading entire assets into RAM


class FileHashError(ValueError):
    """Base exception for file hashing errors."""
    code = "file_hash.error"


class HashMismatchError(FileHashError):
    """Raised when file content does not match expected SHA-256."""
    code = "file_hash.mismatch"


def sha256_file(path: Union[str, Path], chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """
    Compute lowercase canonical SHA-256 hex digest for a file.
    Streams in chunks to avoid high RAM usage on large 3D models or textures.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")

    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def file_size(path: Union[str, Path]) -> int:
    """Return size of file in bytes."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    return p.stat().st_size


def verify_sha256(path: Union[str, Path], expected_hex: str) -> bool:
    """
    Verify file matches expected SHA-256 hex digest.
    Returns True on match.
    Raises HashMismatchError if mismatched.
    Raises ValueError if expected_hex is malformed.
    """
    if not isinstance(expected_hex, str):
        raise ValueError("Expected SHA-256 hash must be a string")
    
    clean_expected = expected_hex.strip().lower()
    if len(clean_expected) != 64 or not all(c in "0123456789abcdef" for c in clean_expected):
        raise ValueError(f"Invalid SHA-256 hex format: '{expected_hex}' (must be 64 hex characters)")

    actual_hex = sha256_file(path)
    if actual_hex != clean_expected:
        raise HashMismatchError(
            f"Hash mismatch for '{path}': expected {clean_expected}, got {actual_hex}"
        )
    return True
