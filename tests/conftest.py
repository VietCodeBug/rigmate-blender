"""Cấu hình fixtures và mock bpy cho kiểm thử pytest."""

import sys
import pytest
from pathlib import Path

# Đảm bảo src/ nằm trong sys.path
root_dir = Path(__file__).resolve().parent.parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Fixture cung cấp thư mục lưu trữ tạm thời cho từng test case."""
    storage_dir = tmp_path / "rigmate_test_storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir
