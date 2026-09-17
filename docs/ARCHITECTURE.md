# Kiến Trúc Hệ Thống RigMate (Architecture Design)

## 1. Nguyên Tắc Thiết Kế Cốt Lõi

1. **Tách Biệt Độc Lập Khỏi Blender (`bpy`)**:
   - Mọi cấu trúc dữ liệu (`core/models.py`), thuật toán chẩn đoán (`core/analyzer.py`), bộ nhớ lưu trữ (`storage/manager.py`) và nhà cung cấp AI (`providers/`) phải chạy được trên Python thuần túy mà không cần `bpy`.
   - Điều này cho phép CI/CD, unit test và mô phỏng chạy tức thì trên bất kỳ máy chủ nào mà không đòi hỏi cài đặt Blender.

2. **Bất Đồng Bộ & An Toàn Luồng (Thread Safety)**:
   - **Main Thread của Blender**: Chỉ thực thi các thao tác can thiệp trực tiếp vào scene (`bpy.context`, `bpy.data`, `bpy.ops`).
   - **Background Worker**: Client mạng (`RigMateBridgeClient`) chạy trên daemon thread riêng biệt để gửi nhận HTTP/JSON, đảm bảo giao diện 3D View của Blender không bao giờ bị đơ (freeze).
   - Khi có dữ liệu trả về từ AI Bridge, kết quả được đẩy ngược vào Main Thread an toàn thông qua `bpy.app.timers.register`.

3. **Bảo Mật Cục Bộ (Localhost Security)**:
   - Bridge Server chỉ `bind` vào địa chỉ `127.0.0.1`.
   - Mỗi lần khởi động, Bridge sinh một `auth_token` ngẫu nhiên 32 ký tự hex và yêu cầu Header `x-rigmate-token` trên mọi request nhạy cảm (tránh tấn công CSRF từ trình duyệt hoặc truy cập từ mạng LAN nội bộ).

---

## 2. Sơ Đồ Khối Tương Tác

```text
+-------------------------------------------------------------------------+
|                              BLENDER PROCESS                            |
|                                                                         |
|  [3D Viewport] <---> [RigMate Sidebar UI (N-Panel)]                    |
|                              |                                          |
|                 [Operators & Timers (Main Thread)]                      |
|                              |                                          |
|               [BpyInspector (Trích xuất Metadata)]                      |
|                              |                                          |
|             [RigMateBridgeClient (Background Worker Thread)]            |
+------------------------------|------------------------------------------+
                               | (HTTP / JSON localhost:8765)
                               v
+-------------------------------------------------------------------------+
|                         RIGMATE BRIDGE PROCESS                          |
|                                                                         |
|  [FastAPI Bridge Server (127.0.0.1)]                                    |
|         |                                                               |
|         +---> [SessionManager] <---> [StorageManager (Atomic JSON)]     |
|         |                                                               |
|         +---> [AI Provider Dispatcher]                                  |
|                     |                                                   |
|                     +---> [MockAIProvider] (Sẵn sàng khi dev/test)      |
|                     |                                                   |
|                     +---> [AntigravityProvider] (Adapter agy / SDK)     |
|                                                                         |
|  [MCP Server (FastMCP - Model Context Protocol)]                        |
|         +--- inspect_scene                                              |
|         +--- inspect_mesh                                               |
|         +--- inspect_armature                                           |
|         +--- diagnose_rig                                               |
+-------------------------------------------------------------------------+
```

---

## 3. Quản Lý Hạn Mức & Thanh Năng Lượng (Energy Bar)

Để đảm bảo tính trung thực và minh bạch theo mục 5 của đặc tả sản phẩm:
- `QuotaSnapshot` lưu giữ:
  - `quota_remaining` và `quota_total`: Chỉ tính phần trăm khi cả hai trường đều có giá trị hợp lệ.
  - `source`: Ghi nhãn tường minh `AUTOMATIC`, `MANUAL`, `DEMO` hoặc `UNKNOWN`.
  - `is_stale`: Tự động cảnh báo nếu snapshot cũ hơn 24 giờ.
  - `plan_expiration`: Thời hạn thuê bao tách biệt hoàn toàn với chu kỳ reset hạn mức ngày/tháng (`reset_at`).
  - `last_tokens_used`: Token tiêu thụ của lượt chat đơn lẻ được hiển thị riêng, không tự tiện cấn trừ suy đoán vào quota tổng.
