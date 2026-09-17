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

    # Explicit allowlist of files needed inside Blender runtime
    # All placed directly inside the 'rigmate/' root package in the zip
    blender_addon_dir = src_dir / "blender_addon"
    allowlist_files = [
        "__init__.py",
        "ui.py",
        "operators.py",
        "client.py",
        "bpy_inspectors.py",
        "dto.py",
        "i18n.py",
        "analyzer.py",
    ]

    files_to_pack = []
    for fname in allowlist_files:
        src_file = blender_addon_dir / fname
        if not src_file.is_file():
            raise FileNotFoundError(f"Required addon file missing: {src_file}")
        files_to_pack.append((src_file, Path("rigmate") / fname))

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

        # 1. Check mandatory runtime files
        required_files = [
            "rigmate/__init__.py",
            "rigmate/ui.py",
            "rigmate/operators.py",
            "rigmate/client.py",
            "rigmate/bpy_inspectors.py",
            "rigmate/dto.py",
            "rigmate/i18n.py",
            "rigmate/analyzer.py",
        ]

        for req in required_files:
            assert req in names, f"Missing required file in ZIP: {req}"
            print(f"  [PASS] Required file present: {req}")

        # 2. Check that external backend infrastructure is NOT packaged
        forbidden_inclusions = [
            "rigmate/core/jobs.py",
            "rigmate/core/job_service.py",
            "rigmate/core/plans.py",
            "rigmate/core/checkpoints.py",
            "rigmate/core/receipts.py",
            "rigmate/core/recovery.py",
            "rigmate/core/models.py",
            "rigmate/storage/job_store.py",
            "rigmate/storage/checkpoints.py",
            "rigmate/storage/idempotency.py",
            "rigmate/bridge/server.py",
            "rigmate/mcp_server/server.py",
            "pydantic",
            "fastapi",
        ]
        for fbd in forbidden_inclusions:
            assert fbd not in names, f"Forbidden server/core module accidentally packaged: {fbd}"

        # 3. Check for secrets / cache / tests / unwanted files
        forbidden_patterns = [".git", "__pycache__", "pytest", "tests/", ".tmp", "token", ".key"]
        for n in names:
            for p in forbidden_patterns:
                assert p not in n.lower(), f"Unwanted file or cache pattern detected in ZIP: {n}"

        print("  [PASS] No sensitive files, cache, or tests detected in ZIP.")
        print("  [PASS] External Python/server infrastructure excluded from ZIP.")

        # 4. AST syntax check on all packaged Python files
        for n in names:
            if n.endswith(".py"):
                content = zipf.read(n).decode("utf-8")
                try:
                    ast.parse(content)
                    print(f"  [PASS] AST Syntax Check: {n}")
                except SyntaxError as e:
                    raise AssertionError(f"Syntax error in packaged file {n}: {e}")

    print("--- ADD-ON ZIP VALIDATION COMPLETE: 100% VALID! ---")


if __name__ == "__main__":
    package_blender_addon()
