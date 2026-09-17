"""Kiểm thử RuntimeStateManager: Ghi atomic, đọc token, stale detection, file hỏng."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from rigmate.storage.runtime_state import RuntimeStateManager, BridgeRuntimeState


def test_runtime_state_save_and_load(temp_storage_dir):
    manager = RuntimeStateManager(base_dir=temp_storage_dir)

    state = BridgeRuntimeState(
        host="127.0.0.1",
        port=8765,
        auth_token="test_secret_token_12345",
        pid=9999,
        version="0.1.0",
    )
    manager.save_state(state)

    loaded = manager.load_state(check_stale=True)
    assert loaded is not None
    assert loaded.auth_token == "test_secret_token_12345"
    assert loaded.host == "127.0.0.1"
    assert loaded.port == 8765
    assert loaded.pid == 9999


def test_runtime_state_stale_detection(temp_storage_dir):
    manager = RuntimeStateManager(base_dir=temp_storage_dir)

    # Tạo state từ 24h trước
    old_time = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    old_state = BridgeRuntimeState(
        auth_token="stale_token",
        started_at=old_time,
    )
    manager.save_state(old_state)

    # Đọc với check_stale=True phải trả về None
    assert manager.load_state(check_stale=True) is None
    # Đọc với check_stale=False vẫn trả về state
    assert manager.load_state(check_stale=False) is not None


def test_runtime_state_corrupted_file(temp_storage_dir):
    manager = RuntimeStateManager(base_dir=temp_storage_dir)

    # Ghi dữ liệu rác
    with open(manager.state_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json corrupted state ")

    # Hệ thống tự động phục hồi an toàn, trả về None, không crash
    assert manager.load_state() is None


def test_runtime_state_cleanup(temp_storage_dir):
    manager = RuntimeStateManager(base_dir=temp_storage_dir)
    state = BridgeRuntimeState(auth_token="tok")
    manager.save_state(state)
    assert manager.state_file.exists()

    manager.clear_state()
    assert not manager.state_file.exists()
