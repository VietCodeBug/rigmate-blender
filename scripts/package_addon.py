"""Script đóng gói add-on Blender thành file .zip sẵn sàng cài đặt qua Blender Preferences."""

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


def package_blender_addon():
    root_dir = Path(__file__).resolve().parent.parent
    addon_src = root_dir / "src" / "rigmate" / "blender_addon"
    dist_dir = root_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    zip_output_path = dist_dir / "rigmate_blender_addon_v0.1.0.zip"

    print(f"Đang đóng gói add-on từ: {addon_src}")
    print(f"File zip đầu ra: {zip_output_path}")

    # Tạo tệp zip chứa thư mục rigmate_addon
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in addon_src.rglob("*"):
            if file.is_file() and "__pycache__" not in file.parts and not file.name.endswith(".pyc"):
                # Đường dẫn tương đối bên trong zip
                rel_path = Path("rigmate") / file.relative_to(addon_src)
                zipf.write(file, rel_path)
                print(f"  + Đã thêm: {rel_path}")

    print(f"\n-> Hoàn tất đóng gói! Kích thước: {os.path.getsize(zip_output_path)} bytes.")
    print("Người dùng có thể vào Blender: Edit > Preferences > Add-ons > Install... và chọn file zip này.")


if __name__ == "__main__":
    package_blender_addon()
