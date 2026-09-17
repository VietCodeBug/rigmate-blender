# QUYẾT ĐỊNH KIẾN TRÚC KỸ THUẬT (ARCHITECTURAL DECISIONS)

Tài liệu này lưu giữ các quyết định kiến trúc quan trọng (ADR - Architecture Decision Records) của RigMate, lý do lựa chọn và các phương án đánh đổi.

---

## ADR-01: Xác thực Local Bridge qua Runtime State Discovery
- **Bối cảnh**: Bridge Server và Blender Add-on là hai process riêng biệt chạy trên cùng một máy tính cá nhân. Bridge cần bảo vệ các endpoint POST nhạy cảm (`/chat`, `/cancel`, `/quota/manual`) để tránh request giả mạo hoặc CSRF từ trình duyệt, nhưng người dùng không nên phải copy-paste token thủ công mỗi lần mở Blender.
- **Quyết định**:
  - Khi Bridge khởi động, sinh token ngẫu nhiên an toàn `secrets.token_hex(16)`.
  - Ghi runtime state gồm `host`, `port`, `auth_token`, `pid`, `started_at` vào file `bridge_state.json` trong thư mục AppData cục bộ của hệ điều hành (`%LOCALAPPDATA%\RigMate` trên Windows).
  - File được ghi nguyên tử (Atomic write qua temporary file) để tránh race condition hoặc hỏng file khi crash.
  - Blender client tự động đọc `bridge_state.json` khi bấm "Kiểm tra" hoặc gửi request đầu tiên. Có cơ chế kiểm tra `is_stale()` (nếu quá 12 giờ hoặc server cũ đã tắt).
  - Không bao giờ commit token vào Git và không lưu token trong thư mục repository.
- **Hệ quả**: Kết nối diễn ra hoàn toàn tự động (zero-config) đối với người dùng mà vẫn đảm bảo 100% request được bảo vệ bởi xác thực token.

---

## ADR-02: Ranh Giới Đóng Gói Giữa Blender Python và External Python
- **Bối cảnh**: Blender đi kèm với một môi trường Python nội bộ (Embedded Python). Người dùng không nên (và thường không thể) cài đặt các dependency nặng (FastAPI, Uvicorn, PyTorch, Pytest...) vào Python của Blender.
- **Quyết định**:
  - Chia hệ thống thành 2 phân vùng rõ rệt:
    1. **Blender Add-on Runtime**: Chạy trong Blender Python, chỉ phụ thuộc vào `bpy`, `mathutils`, thư viện chuẩn (`urllib`, `json`, `threading`), cùng hai package nhẹ được đóng gói kèm: `rigmate.core` và `rigmate.storage`.
    2. **Bridge & MCP Runtime**: Chạy trong môi trường Python ngoài (Virtual Environment), chứa FastAPI, Uvicorn, Pydantic, MCP SDK, AI Provider adapters.
  - Khi script `scripts/package_addon.py` đóng gói, nó đưa cả `core/` và `storage/` vào thư mục `rigmate/` của ZIP để khi giải nén vào `scripts/addons/rigmate/`, các import nội bộ `from rigmate.core...` đều phân giải chính xác mà không đòi hỏi cài đặt gói rigmate ngoài hệ thống.
- **Hệ quả**: Add-on cài đặt thành công 1-click qua Blender Preferences mà không bị lỗi thiếu package hoặc xung đột thư viện.

---

## ADR-03: Tính Minh Bạch Tuyệt Đối Của Hạn Mức & Thanh Năng Lượng (Quota Truthfulness)
- **Bối cảnh**: Các nhà cung cấp AI thường có cách tính hạn mức khác nhau (theo ngày, theo tháng, theo credits hoặc theo token). Việc tự động suy diễn phần trăm khi thiếu dữ liệu dễ gây hiểu nhầm nghiêm trọng cho người dùng.
- **Quyết định**:
  - Phân tách rõ 3 đại lượng:
    1. `last_tokens_used`: Token tiêu thụ của lượt/phiên chat hiện tại (Prompt + Completion).
    2. `quota_remaining`: Hạn mức tài khoản còn lại.
    3. `plan_expiration`: Thời hạn thuê bao gói (trường riêng biệt, không gộp với chu kỳ reset quota hàng ngày/tháng).
  - Nguồn dữ liệu phải gắn nhãn rõ ràng:
    - `[Tự động]`: Khi nhà cung cấp có API máy đọc.
    - `[Nhập thủ công]`: Khi người dùng nhập snapshot từ `/usage`.
    - `[DEMO]`: Khi chạy Mock Provider.
    - `Chưa đọc được hạn mức tự động`: Khi không có dữ liệu máy đọc (source `UNKNOWN`).
  - Thanh năng lượng slider (%) chỉ dựng khi có đầy đủ cả `remaining` và `total > 0`. Nếu không đủ, chỉ hiển thị số lượng thô hoặc nhãn thông báo, tuyệt đối không suy đoán phần trăm giả.
- **Hệ quả**: Giao diện trung thực, đáng tin cậy và không tạo cảm giác AI "ảo tưởng" về tài nguyên.

---

## ADR-04: Giữ Gìn Phiên Hội Thoại & Hủy Tác Vụ Thật (Session Continuity & Cancellation)
- **Bối cảnh**: Khi chat với AI trợ lý rig, ngữ cảnh trao đổi qua các lượt là cốt lõi để AI nhớ đối tượng đang xử lý. Khi người dùng bấm "Dừng lại", thao tác không được chỉ đổi cờ UI mà phải ngắt request đang chạy trên server.
- **Quyết định**:
  - Sau lượt chat đầu tiên, Bridge trả về `session_id`. Blender Add-on lưu `props.active_session_id`.
  - Các lượt chat kế tiếp gửi kèm `active_session_id`.
  - Bấm "Mới" (New Session) xóa `active_session_id` để lượt sau sinh phiên mới.
  - Bấm "Dừng lại" gọi endpoint `POST /cancel` với `session_id`, `SessionManager` gọi `task.cancel()` trên `asyncio.Task` đang chạy trước khi reset trạng thái UI.
