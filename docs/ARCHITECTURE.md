# Kiến Trúc Hệ Thống RigMate (Architecture Design)

Tài liệu này mô tả kiến trúc **thực tế hiện tại** của RigMate v0.1 sau khi đã khắc phục các blocker tích hợp.

---

## 1. Các Nguyên Tắc Thiết Kế

1. **Ranh Giới Rõ Ràng Giữa Blender Python và External Python**:
   - Blender Python: Chạy Add-on UI, Operators, Background Client, và hai package nhẹ được đóng gói trực tiếp vào file ZIP: `rigmate.core` và `rigmate.storage`.
   - External Python: Chạy Bridge Server (FastAPI/Uvicorn), MCP Server (FastMCP), và các AI Provider adapters (Mock, Antigravity).

2. **Xác Thực Cục Bộ Bằng Discovery Token (Zero-Config Security)**:
   - Bridge chỉ bind vào `127.0.0.1`.
   - Token xác thực được sinh ngẫu nhiên và ghi ra runtime state file an toàn trong Local AppData (`%LOCALAPPDATA%\RigMate\bridge_state.json`).
   - Blender Client tự động đọc file này để lấy token thực hiện handshake và ký header `x-rigmate-token` trên các request `/chat`, `/cancel`, `/quota`, `/quota/manual`. Không yêu cầu người dùng copy-paste token thủ công.

3. **An Toàn Luồng (Thread Safety)**:
   - Toàn bộ giao tiếp mạng của Add-on chạy trên daemon background thread của `RigMateBridgeClient`.
   - Kết quả phản hồi được đồng bộ ngược về Main Thread của Blender thông qua `bpy.app.timers.register`.

4. **Dữ Liệu Ngữ Cảnh Gọn Gàng**:
   - Tùy chọn `send_selected_only` sử dụng `BpyInspector.get_selected_context()` chỉ thu thập Active Object và danh sách Selected Objects cùng thông tin tổng quát (vertex count, modifiers, transform status). Tuyệt đối không gửi tọa độ của 50.000 đỉnh lên AI.

---

## 2. Sơ Đồ Khối Thực Tế

```text
+-------------------------------------------------------------------------+
|                              BLENDER PROCESS                            |
|                                                                         |
|  [3D Viewport] <---> [RigMate Sidebar UI (Tab N)]                       |
|                              |                                          |
|                 [Operators (Main Thread)]                               |
|                              |                                          |
|               [BpyInspector.get_selected_context()]                     |
|                              |                                          |
|         [RigMateBridgeClient (Background Daemon Thread)]                |
|               ^                                                         |
|               | (Tự động đọc runtime auth_token)                        |
|               |                                                         |
|         [%LOCALAPPDATA%/RigMate/bridge_state.json]                      |
+------------------------------|------------------------------------------+
                               | (HTTP / JSON localhost:8765)
                               | [Headers: x-rigmate-token]
                               v
+-------------------------------------------------------------------------+
|                         RIGMATE BRIDGE PROCESS                          |
|                                                                         |
|  [FastAPI Bridge Server (127.0.0.1)]                                    |
|         |                                                               |
|         +---> [RuntimeStateManager] -> ghi bridge_state.json            |
|         |                                                               |
|         +---> [SessionManager] (Giữ session_id & hủy task thật)         |
|         |                                                               |
|         +---> [StorageManager] (Atomic write, corrupt backup, Quota)    |
|         |                                                               |
|         +---> [AI Provider Dispatcher]                                  |
|                     |                                                   |
|                     +---> [MockAIProvider] (Hunyuan+Meshy scenarios)    |
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
