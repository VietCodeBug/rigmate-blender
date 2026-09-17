"""Tests for repository structure and package source file integrity."""

from pathlib import Path


def test_required_storage_source_files_exist():
    """Verify that all core storage source files exist in the source tree."""
    root_dir = Path(__file__).resolve().parent.parent
    storage_dir = root_dir / "src" / "rigmate" / "storage"

    required_storage_modules = [
        "__init__.py",
        "paths.py",
        "manager.py",
        "runtime_state.py",
        "retention.py",
        "json_io.py",
        "disk_budget.py",
    ]

    for mod_name in required_storage_modules:
        mod_path = storage_dir / mod_name
        assert mod_path.is_file(), f"Missing required storage source module: {mod_path}"


def test_required_core_source_files_exist():
    """Verify that all foundational core source files exist in the source tree."""
    root_dir = Path(__file__).resolve().parent.parent
    core_dir = root_dir / "src" / "rigmate" / "core"

    required_core_modules = [
        "__init__.py",
        "models.py",
        "analyzer.py",
        "quota.py",
        "i18n.py",
        "path_safety.py",
        "file_hash.py",
        "schema_version.py",
        "project.py",
        "redaction.py",
        "retry.py",
        "errors.py",
        "ids.py",
        "time_utils.py",
        "events.py",
        "operations.py",
        "receipts.py",
        "capabilities.py",
        "support_bundle.py",
        "json_types.py",
    ]

    for mod_name in required_core_modules:
        mod_path = core_dir / mod_name
        assert mod_path.is_file(), f"Missing required core source module: {mod_path}"
