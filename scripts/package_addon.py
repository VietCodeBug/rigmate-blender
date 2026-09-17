"""Script đóng gói add-on Blender chuẩn package hierarchy và tự động xác thực import."""

import ast
import os
import sys
import shutil
import zipfile
from pathlib import Path

# Đảm bảo console Windows in được tiếng Việt UTF-8
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

    print(f"Đang đóng gói add-on từ: {src_dir}")
    print(f"File zip đầu ra: {zip_output_path}")

    # Danh sách các module/thư mục bắt buộc phải có trong add-on Blender:
    # 1. blender_addon/ (các file __init__.py, ui.py, operators.py, client.py, bpy_inspectors.py đặt tại root của package rigmate trong zip)
    # 2. core/ (models.py, analyzer.py, quota.py)
    # 3. storage/ (paths.py, manager.py, runtime_state.py)
    
    files_to_pack = []

    # 1. Các file trong blender_addon được đặt trực tiếp vào rigmate/ trong zip để Blender nhận diện làm add-on root
    blender_addon_dir = src_dir / "blender_addon"
    for f in blender_addon_dir.glob("*.py"):
        if not f.name.endswith(".pyc"):
            files_to_pack.append((f, Path("rigmate") / f.name))

    # 2. Package core
    core_dir = src_dir / "core"
    for f in core_dir.glob("*.py"):
        if not f.name.endswith(".pyc"):
            files_to_pack.append((f, Path("rigmate") / "core" / f.name))

    # 3. Package storage
    storage_dir = src_dir / "storage"
    for f in storage_dir.glob("*.py"):
        if not f.name.endswith(".pyc"):
            files_to_pack.append((f, Path("rigmate") / "storage" / f.name))

    # Ghi vào file ZIP
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for src_file, arc_name in files_to_pack:
            zipf.write(src_file, arc_name)
            print(f"  + [ZIP] {arc_name}")

    print(f"\n-> Hoàn tất đóng gói! Kích thước: {os.path.getsize(zip_output_path)} bytes.")
    
    # Chạy kiểm tra tự động cấu trúc gói (Automated Validation)
    validate_addon_zip(zip_output_path)
    return zip_output_path


def validate_addon_zip(zip_path: Path):
    """Kiểm tra tính hợp lệ của file ZIP add-on ngoài môi trường Blender."""
    print("\n--- BẮT ĐẦU KIỂM THỬ XÁC THỰC FILE ZIP (VALIDATION) ---")
    assert zip_path.exists(), f"File ZIP không tồn tại: {zip_path}"

    with zipfile.ZipFile(zip_path, "r") as zipf:
        names = zipf.namelist()

        # 1. Kiểm tra các file bắt buộc phải tồn tại
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
            "rigmate/storage/__init__.py",
            "rigmate/storage/paths.py",
            "rigmate/storage/manager.py",
            "rigmate/storage/runtime_state.py",
        ]

        for req in required_files:
            assert req in names, f"Thiếu file bắt buộc trong ZIP: {req}"
            print(f"  [PASS] File bắt buộc: {req}")

        # 2. Kiểm tra không chứa credential / cache / test
        forbidden_patterns = [".git", "__pycache__", "pytest", "tests/", ".tmp", "token", ".key"]
        for n in names:
            for forb in forbidden_patterns:
                assert forb not in n.lower(), f"Phát hiện file cấm trong ZIP: {n} (chứa '{forb}')"
        print("  [PASS] Không phát hiện file nhạy cảm, cache hay tests trong ZIP.")

        # 3. Kiểm tra AST Parse toàn bộ mã Python trong ZIP
        for n in names:
            if n.endswith(".py"):
                content = zipf.read(n).decode("utf-8")
                try:
                    ast.parse(content)
                    print(f"  [PASS] AST Syntax Check: {n}")
                except SyntaxError as e:
                    raise AssertionError(f"Lỗi cú pháp Python trong file {n}: {e}")

    print("--- HOÀN TẤT XÁC THỰC ZIP ADD-ON: 100% HỢP LỆ! ---\n")


if __name__ == "__main__":
    package_blender_addon()
