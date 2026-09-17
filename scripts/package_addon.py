"""Script to package Blender add-on with standard hierarchy and automated validation."""

import ast
import os
import sys
import shutil
import zipfile
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def package_blender_addon() -> Path:
    root_dir = Path(__file__).resolve().parent.parent
    src_dir = root_dir / "src" / "rigmate"
    dist_dir = root_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    zip_output_path = dist_dir / "rigmate_blender_addon_v0.1.0.zip"

    print(f"Packaging add-on from: {src_dir}")
    print(f"Destination ZIP: {zip_output_path}")

    # Required structure in add-on package:
    # 1. blender_addon/ contents placed at root of rigmate/ package inside zip
    # 2. core/ (models.py, analyzer.py, quota.py, i18n.py)
    # 3. storage/ (paths.py, manager.py, runtime_state.py)
    
    files_to_pack = []

    # 1. Files in blender_addon placed directly into rigmate/ root in zip
    blender_addon_dir = src_dir / "blender_addon"
    for f in blender_addon_dir.glob("*.py"):
        if not f.name.endswith(".pyc"):
            files_to_pack.append((f, Path("rigmate") / f.name))

    # 2. Core package
    core_dir = src_dir / "core"
    for f in core_dir.glob("*.py"):
        if not f.name.endswith(".pyc"):
            files_to_pack.append((f, Path("rigmate") / "core" / f.name))

    # 3. Storage package
    storage_dir = src_dir / "storage"
    for f in storage_dir.glob("*.py"):
        if not f.name.endswith(".pyc"):
            files_to_pack.append((f, Path("rigmate") / "storage" / f.name))

    # Write ZIP
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for src_file, arc_name in files_to_pack:
            zipf.write(src_file, arc_name)
            print(f"  + [ZIP] {arc_name}")

    print(f"\n-> Packaging complete! Size: {os.path.getsize(zip_output_path)} bytes.")
    
    # Automated ZIP package validation
    validate_addon_zip(zip_output_path)
    return zip_output_path


def validate_addon_zip(zip_path: Path):
    """Validate add-on ZIP package integrity without requiring Blender."""
    print("\n--- VALIDATING ADD-ON ZIP PACKAGE ---")
    assert zip_path.exists(), f"ZIP file not found: {zip_path}"

    with zipfile.ZipFile(zip_path, "r") as zipf:
        names = zipf.namelist()

        # 1. Check mandatory files
        required_files = [
            "rigmate/__init__.py",
            "rigmate/ui.py",
            "rigmate/operators.py",
            "rigmate/client.py",
            "rigmate/bpy_inspectors.py",
            "rigmate/core/__init__.py",
            "rigmate/core/models.py",
            "rigmate/core/analyzer.py",
            "rigmate/core/quota.py",
            "rigmate/core/i18n.py",
            "rigmate/storage/__init__.py",
            "rigmate/storage/paths.py",
            "rigmate/storage/manager.py",
            "rigmate/storage/runtime_state.py",
        ]

        for req in required_files:
            assert req in names, f"Missing required file in ZIP: {req}"
            print(f"  [PASS] Required file present: {req}")

        # 2. Check for secrets / cache / tests / unwanted files
        forbidden_patterns = [".git", "__pycache__", "pytest", "tests/", ".tmp", "token", ".key"]
        for n in names:
            for forb in forbidden_patterns:
                assert forb not in n.lower(), f"Forbidden file detected in ZIP: {n} (contains '{forb}')"
        print("  [PASS] No sensitive files, cache, or tests detected in ZIP.")

        # 3. AST parse all python files in ZIP
        for n in names:
            if n.endswith(".py"):
                content = zipf.read(n).decode("utf-8")
                try:
                    ast.parse(content)
                    print(f"  [PASS] AST Syntax Check: {n}")
                except SyntaxError as e:
                    raise AssertionError(f"Python syntax error in {n}: {e}")

    print("--- ADD-ON ZIP VALIDATION COMPLETE: 100% VALID! ---\n")


if __name__ == "__main__":
    package_blender_addon()

