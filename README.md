# RigMate 🦴🤖

**Trợ lý trong Blender dành cho người dùng ít kiến thức 3D, hỗ trợ kiểm tra và tinh chỉnh rig nhân vật (Hunyuan 3D + Meshy) hướng tới xuất sang Godot Engine.**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.0+](https://img.shields.io/badge/Blender-4.0+-orange.svg)](https://www.blender.org/)
[![Status: v0.1.0](https://img.shields.io/badge/Version-v0.1.0-green.svg)]()

---

## 1. Mục tiêu & Luồng công việc thực tế

Người dùng thông thường thường tạo nhân vật 3D qua quy trình tự động:
1. Tạo mô hình bằng **Tencent Hunyuan 3D** (mật độ lưới thường dày, khoảng ~50.000 đỉnh).
2. Đưa mô hình sang **Meshy** để tự động gắn khung xương (Auto-rig cơ bản).
3. Nhập nhân vật vào **Blender**.
4. **RigMate** đồng hành trợ lý: chẩn đoán các lỗi unapplied transforms, cảnh báo số đỉnh quá dày cho Game Engine, nhận diện cấu trúc xương ngón tay (heuristic), và chuẩn bị sẵn sàng để xuất sang **Godot**.

> **Triết lý sản phẩm:**
> - Không giả định mọi mô hình đều có 5 ngón tay tách rời hoặc topology hoàn hảo.
> - Tên xương chỉ là gợi ý, không áp đặt kết luận sai lệch.
> - Bản v0.1 tập trung vào **quan sát, chẩn đoán và hội thoại trợ lý**.

---

## 2. Điểm nổi bật ở phiên bản v0.1

- 🔋 **Thanh năng lượng & Hạn mức AI minh bạch**:
  - Tách bạch 3 khái niệm: Token tiêu thụ theo lượt/phiên, Hạn mức Quota còn lại, và Thời hạn gói thuê bao.
  - Phân biệt rõ nguồn dữ liệu: `[Tự động]`, `[Nhập thủ công]` hoặc `[DEMO]`.
  - Không tự đoán mò hạn mức nếu nhà cung cấp chưa có API máy đọc.
- 💬 **Hội thoại ngay trong Blender**:
  - Giao diện tab RigMate trong Sidebar (phím `N` trong 3D View).
  - Quản lý phiên hội thoại, lưu trữ cục bộ, nút gửi, nút dừng tác vụ đang chạy.
  - Tùy chọn chỉ gửi thông tin object/vùng chọn, không tự tiện tải toàn bộ mesh dung lượng lớn.
- 🛠️ **Bộ công cụ MCP (Model Context Protocol)**:
  - `inspect_scene`: Đọc tổng quan Scene Blender.
  - `inspect_mesh`: Đọc thông tin chi tiết Mesh (số đỉnh, modifiers, vertex groups).
  - `inspect_armature`: Đọc hệ thống xương, phân cấp cha-con.
  - `diagnose_rig`: Chẩn đoán tự động tương thích Godot.
- 🔒 **Bảo mật & Dữ liệu Cục bộ**:
  - Giao tiếp Localhost an toàn với Token xác thực ngẫu nhiên theo phiên.
  - Lưu trữ JSON nguyên tử (Atomic write), tự phục hồi khi gặp file hỏng, hỗ trợ tiếng Việt có dấu 100%.

---

## 3. Cấu trúc Dự án

```text
RigMate/
├── .gitignore
├── LICENSE (GPL-3.0-or-later)
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── HOME_SETUP_GUIDE.md
│   └── BLENDER_TESTING_CHECKLIST.md
├── scripts/
│   ├── run_demo.py               # Chạy demo tương tác không cần cài Blender
│   └── package_addon.py          # Đóng gói add-on thành file zip
├── src/
│   └── rigmate/
│       ├── core/                 # Cấu trúc dữ liệu & phân tích rig độc lập bpy
│       ├── storage/              # Lưu trữ cục bộ an toàn, atomic write
│       ├── providers/            # AI Providers (Mock + Antigravity CLI/SDK)
│       ├── bridge/               # Bridge server localhost quản lý session
│       ├── mcp_server/           # Máy chủ công cụ MCP FastMCP
│       └── blender_addon/        # Add-on tích hợp trong Blender
└── tests/                        # Toàn bộ unit tests tự động (pytest)
```

---

## 4. Hướng dẫn chạy thử nghiệm nhanh (Không cần Blender)

Trên máy chưa cài đặt Blender, bạn hoàn toàn có thể kiểm thử toàn bộ logic chẩn đoán, phiên chat và lưu trữ:

### Bước 1: Chạy kiểm thử tự động
```powershell
python -m pytest tests -v
```

### Bước 2: Chạy demo tương tác Console
```powershell
python scripts/run_demo.py
```

### Bước 3: Đóng gói Add-on
```powershell
python scripts/package_addon.py
```
Tệp `.zip` cài đặt sẽ được tạo tại: `dist/rigmate_blender_addon_v0.1.0.zip`.

---

## 5. Hướng dẫn cài đặt và kết nối tại nhà (Có Blender)

Xem chi tiết tại [Tài liệu hướng dẫn tại nhà](docs/HOME_SETUP_GUIDE.md) và [Checklist kiểm thử Blender](docs/BLENDER_TESTING_CHECKLIST.md).

Tóm tắt các bước:
1. Mở Blender > `Edit` > `Preferences` > `Add-ons` > `Install...` > Chọn `dist/rigmate_blender_addon_v0.1.0.zip`.
2. Kích hoạt add-on **RigMate - AI Rig Assistant**.
3. Khởi chạy Bridge Server trên terminal:
   ```powershell
   python -m uvicorn rigmate.bridge.server:BridgeServer().app --host 127.0.0.1 --port 8765
   ```
4. Trong Blender 3D View, bấm phím `N` để mở Sidebar, chọn tab **RigMate** và nhấn **Kiểm tra kết nối**.

---

## 6. Lưu ý về Quyền riêng tư & AI

- Dữ liệu lịch sử trò chuyện và cấu hình được lưu hoàn toàn trên máy tính cá nhân trong thư mục AppData/Local của người dùng.
- **Lưu cục bộ không có nghĩa là AI chạy offline**: Khi bạn bấm "Gửi", câu hỏi và dữ liệu phân tích ngữ cảnh của đối tượng mà bạn đồng ý gửi sẽ được chuyển tới Provider AI (Antigravity/Gemini) để xử lý.
- RigMate tuyệt đối không thu thập mật khẩu, cookie hay tự động bật các gói tính phí ngoài ý muốn của người dùng.

---

## 7. Giấy phép

Dự án được phát hành theo giấy phép **GNU General Public License v3.0 or later (GPL-3.0-or-later)** để tương thích hoàn toàn với hệ sinh thái Blender.
