# Hướng Dẫn Cài Đặt Và Kết Nối Tại Nhà (Home Setup Guide)

Tài liệu này hướng dẫn chi tiết cách thiết lập và kết nối RigMate trên máy cá nhân có sẵn Blender và tài khoản AI.

---

## 1. Yêu Cầu Môi Trường Tại Nhà
- **Hệ điều hành**: Windows 10/11, macOS hoặc Linux.
- **Blender**: Phiên bản 4.0 trở lên.
- **Python**: Phiên bản 3.10 trở lên.
- **Antigravity CLI**: Đã cài đặt lệnh `agy` hoặc package `google-antigravity` (tùy chọn, nếu muốn dùng AI thật thay vì Mock).

---

## 2. Các Bước Cài Đặt Chi Tiết

### Bước 1: Sao chép mã nguồn về máy
Clone repository từ GitHub:
```bash
git clone https://github.com/VietCodeBug/rigmate-blender.git
cd rigmate-blender
```

### Bước 2: Tạo môi trường ảo và cài đặt dependencies
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[bridge,dev]"
```

### Bước 3: Đóng gói Add-on Blender
Chạy script đóng gói:
```powershell
python scripts/package_addon.py
```
Tệp `dist/rigmate_blender_addon_v0.1.0.zip` sẽ được tạo ra kèm thông báo `100% HỢP LỆ`.

### Bước 4: Cài đặt Add-on vào Blender
1. Mở Blender.
2. Vào menu: `Edit` > `Preferences...` > `Add-ons`.
3. Bấm vào nút `Install...` ở góc trên bên phải.
4. Điều hướng tới file `dist/rigmate_blender_addon_v0.1.0.zip` và bấm **Install Add-on**.
5. Tích chọn ô **RigMate - AI Rig Assistant** để kích hoạt.

### Bước 5: Khởi chạy RigMate Bridge Server
Trong terminal (môi trường ảo `venv`):
```powershell
python -m rigmate.bridge --host 127.0.0.1 --port 8765
```
Bridge Server sẽ khởi động, sinh token an toàn và tự động ghi vào `%LOCALAPPDATA%\RigMate\bridge_state.json`.

### Bước 6: Sử dụng ngay trong Blender
1. Trong 3D Viewport, bấm phím `N` để mở Sidebar, chọn tab **RigMate**.
2. Bấm **Kiểm tra**: Add-on sẽ tự động nhận diện token từ Bridge và báo trạng thái xanh `Đã kết nối`.
3. Nhập câu hỏi vào ô chat hoặc chọn mô hình và bấm **Chẩn đoán nhanh Scene/Rig**.
