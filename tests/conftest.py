"""Configuration fixtures and path setup for pytest suite."""

import sys
import pytest
from pathlib import Path

# Ensure src/ is on sys.path
root_dir = Path(__file__).resolve().parent.parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Fixture providing isolated temporary storage directory for tests."""
    storage_dir = tmp_path / "rigmate_test_storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir
