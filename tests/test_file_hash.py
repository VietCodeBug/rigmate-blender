"""Unit tests for streaming file hash and metadata verification."""

from pathlib import Path
import pytest
from rigmate.core.file_hash import (
    sha256_file,
    file_size,
    verify_sha256,
    HashMismatchError,
)


def test_file_hash_empty_file(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_bytes(b"")

    expected_empty_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_file(p) == expected_empty_sha256
    assert file_size(p) == 0
    assert verify_sha256(p, expected_empty_sha256) is True


def test_file_hash_normal_text(tmp_path):
    p = tmp_path / "hello.txt"
    p.write_text("RigMate Assistant v0.1", encoding="utf-8")

    h = sha256_file(p)
    assert len(h) == 64
    assert h == h.lower()
    assert verify_sha256(p, h) is True


def test_file_hash_binary_and_unicode_filename(tmp_path):
    p = tmp_path / "tệp_nhị_phân_ký_tự.bin"
    binary_content = bytes(range(256)) * 10
    p.write_bytes(binary_content)

    assert file_size(p) == 2560
    h = sha256_file(p)
    assert verify_sha256(p, h) is True


def test_file_hash_mismatch_and_malformed_input(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text("data", encoding="utf-8")

    wrong_hash = "0" * 64
    with pytest.raises(HashMismatchError):
        verify_sha256(p, wrong_hash)

    # Malformed length
    with pytest.raises(ValueError, match="Invalid SHA-256 hex format"):
        verify_sha256(p, "short_hash")

    # Non-hex characters
    with pytest.raises(ValueError, match="Invalid SHA-256 hex format"):
        verify_sha256(p, "z" * 64)


def test_file_hash_streaming_large_file(tmp_path):
    # Test that chunked streaming processes 256 KB file correctly
    p = tmp_path / "stream_test.dat"
    chunk = b"A" * 65536  # 64 KB
    with open(p, "wb") as f:
        for _ in range(4):
            f.write(chunk)

    assert file_size(p) == 256 * 1024
    h = sha256_file(p, chunk_size=32 * 1024)
    assert len(h) == 64
    assert verify_sha256(p, h) is True
