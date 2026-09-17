# Hướng Dẫn Cài Đặt Và Kết Nối Tại Nhà (Home Setup Guide)

Tài liệu này dành cho bạn khi về nhà và tiến hành kiểm thử trên máy cá nhân có đầy đủ Blender và Antigravity CLI.

---

## 1. Yêu Cầu Môi Trường Tại Nhà
- **Hệ điều hành**: Windows 10/11, macOS hoặc Linux.
- **Blender**: Phiên bản 4.0 trở lên.
- **Python**: Phiên bản 3.10 trở lên (khuyến nghị Python 3.11 hoặc 3.12).
- **Antigravity CLI**: Đã cài đặt lệnh `agy` hoặc package `google-antigravity`.

---

## 2. Các Bước Cài Đặt Chi Tiết

### Bước 1: Sao chép mã nguồn về máy
Sao chép thư mục dự án `RigMate` hoặc clone từ Git.

### Bước 2: Tạo môi trường ảo và cài đặt dependencies cho Bridge
Mở terminal tại thư mục `RigMate`:
```powershell
# Tạo môi trường ảo riêng cho Bridge & MCP
python -m venv venv
.\venv\Scripts\Activate.ps1

# Cài đặt các gói phụ thuộc
pip install -e ".[bridge,dev]"
```

### Bước 3: Đóng gói Add-on Blender
Chạy script đóng gói:
```powershell
python scripts/package_addon.py
```
Tệp `dist/rigmate_blender_addon_v0.1.0.zip` sẽ được tạo ra.

### Bước 4: Cài đặt Add-on vào Blender
1. Mở Blender.
2. Vào menu: `Edit` > `Preferences...` > `Add-ons`.
3. Bấm vào nút `Install...` ở góc trên bên phải.
4. Điều hướng tới file `dist/rigmate_blender_addon_v0.1.0.zip` và bấm **Install Add-on**.
5. Đánh dấu tích chọn ô **RigMate - AI Rig Assistant** để kích hoạt.

### Bước 5: Khởi chạy RigMate Bridge Server
Trong terminal đã kích hoạt môi trường ảo:
```powershell
python -m uvicorn rigmate.bridge.server:BridgeServer().app --host 127.0.0.1 --port 8765
```
Bridge Server sẽ khởi động và lắng nghe tại `http://127.0.0.1:8765`.

### Bước 6: Kiểm tra kết nối trong Blender
1. Trong màn hình 3D Viewport của Blender, bấm phím `N` trên bàn phím để mở thanh công cụ Sidebar bên phải.
2. Nhấp vào tab **RigMate**.
3. Bấm nút **Kiểm tra kết nối**. Trạng thái sẽ chuyển sang màu xanh: `Đã kết nối (mock)` hoặc `Đã kết nối (antigravity)`.

---

## 3. Chuyển Đổi Sang Antigravity CLI / SDK Thật

Mặc định RigMate khởi chạy với **Mock Provider** an toàn. Để kết nối với tài khoản Antigravity thật của bạn:

1. Đảm bảo bạn đã đăng nhập vào CLI chính thức:
   ```bash
   agy
   # Làm theo hướng dẫn trên màn hình để xác thực tài khoản Google của bạn
   ```
2. Trong file cấu hình Bridge hoặc tham số khởi chạy, chuyển provider sang Antigravity:
   ```python
   from rigmate.bridge.server import BridgeServer
   from rigmate.providers.antigravity_provider import AntigravityProvider

   server = BridgeServer()
   server.set_provider(AntigravityProvider(model="gemini-3.8-flash"))
   ```
3. Sau khi kết nối, RigMate sẽ sử dụng tài khoản cá nhân của bạn thông qua CLI mà **không bao giờ hỏi mật khẩu** hay trích xuất token nội bộ trong add-on.
