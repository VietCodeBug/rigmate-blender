"""Tests for storage resilience: atomic writes, corrupt file recovery, UTF-8/Unicode data, export, and clear."""

import json
from pathlib import Path
import pytest
from rigmate.storage.manager import StorageManager
from rigmate.core.quota import QuotaSnapshot


def test_storage_atomic_and_vietnamese_unicode(temp_storage_dir):
    manager = StorageManager(base_dir=temp_storage_dir)

    session_id = "session-vietnamese-01"
    # Ensure localized strings in user conversations persist correctly without Unicode corruptions
    messages = [
        {"role": "user", "content": "Xin chào! Kiểm tra giúp tôi mô hình Tencent Hunyuan 3D này."},
        {"role": "assistant", "content": "Chào bạn! Tôi phát hiện mô hình có 52,400 đỉnh và các ngón tay chưa tách rời."},
    ]

    # Save data
    manager.save_chat_history(session_id, messages)

    # Read back and verify Unicode integrity
    loaded = manager.load_chat_history(session_id)
    assert len(loaded) == 2
    assert loaded[0]["content"] == "Xin chào! Kiểm tra giúp tôi mô hình Tencent Hunyuan 3D này."
    assert "52,400 đỉnh" in loaded[1]["content"]

    # Verify disk JSON encoding is UTF-8
    with open(manager.history_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
        assert session_id in disk_data


def test_storage_corrupted_file_recovery(temp_storage_dir):
    manager = StorageManager(base_dir=temp_storage_dir)

    # Write corrupt data to test recovery
    with open(manager.history_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json content: [ truncated... ")

    # Must not crash; should create a backup .corrupt.bak and return empty history
    loaded = manager.load_chat_history("non-existent-session")
    assert loaded == []

    # Check corrupt backup file existence
    corrupt_backup = manager.history_file.with_suffix(".corrupt.bak")
    assert corrupt_backup.exists()


def test_storage_quota_snapshot_and_profile_isolation(temp_storage_dir):
    manager = StorageManager(base_dir=temp_storage_dir)

    snap_user_a = QuotaSnapshot(
        provider_name="Antigravity",
        model_name="gemini-3.8-flash",
        account_profile="user_a",
        source="MANUAL",
        quota_remaining=50.0,
        quota_total=100.0,
    )
    snap_user_b = QuotaSnapshot(
        provider_name="Antigravity",
        model_name="gemini-3.8-flash",
        account_profile="user_b",
        source="DEMO",
        quota_remaining=90.0,
        quota_total=100.0,
    )

    manager.save_quota_snapshot(snap_user_a)
    manager.save_quota_snapshot(snap_user_b)

    # Ensure profile snapshots do not collide
    loaded_a = manager.load_quota_snapshot("user_a", "Antigravity", "gemini-3.8-flash")
    loaded_b = manager.load_quota_snapshot("user_b", "Antigravity", "gemini-3.8-flash")

    assert loaded_a is not None and loaded_a.quota_remaining == 50.0
    assert loaded_b is not None and loaded_b.quota_remaining == 90.0

    # Invalidate profile a
    manager.invalidate_snapshots_for_profile("user_a")
    assert manager.load_quota_snapshot("user_a", "Antigravity", "gemini-3.8-flash") is None
    assert manager.load_quota_snapshot("user_b", "Antigravity", "gemini-3.8-flash") is not None


def test_storage_export_and_clear(temp_storage_dir):
    manager = StorageManager(base_dir=temp_storage_dir)
    manager.save_chat_history("s1", [{"role": "user", "content": "test export"}])

    export_file = temp_storage_dir / "rigmate_export.json"
    manager.export_all_data(export_file)

    assert export_file.exists()
    with open(export_file, "r", encoding="utf-8") as f:
        exported = json.load(f)
        assert "chat_history" in exported
        assert "s1" in exported["chat_history"]

    # Clear history
    manager.clear_all_history()
    assert manager.load_chat_history("s1") == []

