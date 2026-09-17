# Hướng Dẫn Đóng Góp Cho RigMate (Contributing Guidelines)

Cảm ơn bạn đã quan tâm đóng góp cho dự án mã nguồn mở **RigMate**!

Dự án phát triển với mục tiêu giúp người sáng tạo nội dung, nghệ sĩ độc lập và nhà phát triển game indie ít kiến thức 3D dễ dàng biến các mô hình AI thành nhân vật game hoạt họa chất lượng cao.

---

## 1. Nguyên Tắc Ứng Xử & Tiêu Chuẩn Kỹ Thuật

- **Giấy phép Bản quyền**: Mọi đóng góp mã nguồn được phát hành theo giấy phép **GPL-3.0-or-later**.
- **Độc lập Bpy**: Không import trực tiếp `bpy` vào các package `rigmate.core`, `rigmate.storage`, `rigmate.providers`. Toàn bộ logic chẩn đoán phải chạy được độc lập với Blender.
- **Tiếng Việt & Quốc tế**: Hỗ trợ tiếng Việt đầy đủ cho giao diện người dùng và tài liệu hướng dẫn. Code, biến, comment kỹ thuật viết bằng tiếng Anh hoặc tiếng Việt nhất quán.
- **Kiểm thử bắt buộc**: Mọi tính năng mới hoặc bản sửa lỗi (bug fix) phải đi kèm unit test trong thư mục `tests/`.

---

## 2. Quy Trình Phát Triển

1. **Fork** repository và tạo một branch mới từ `main`:
   ```bash
   git checkout -b feature/ten-tinh-nang-moi
   ```
2. Cài đặt môi trường phát triển:
   ```bash
   pip install -e ".[bridge,dev]"
   ```
3. Chạy kiểm thử để đảm bảo mọi bài test hiện tại đều đạt:
   ```bash
   python -m pytest tests -v
   ```
4. Thực hiện các thay đổi mã nguồn và bổ sung bài test tương ứng.
5. Kiểm tra code style và commit với thông điệp rõ ràng theo chuẩn Conventional Commits:
   - `feat: thêm thuật toán nhận diện đối xứng xương`
   - `fix: sửa lỗi tính toán phần trăm thanh năng lượng khi quota_total bằng 0`
   - `docs: bổ sung hướng dẫn chạy MCP server`
6. Tạo **Pull Request (PR)** mô tả rõ mục đích và kết quả kiểm thử.

---

## 3. Báo Lỗi & Đề Xuất Tính Năng

Nếu bạn gặp lỗi hoặc có ý tưởng cải tiến, vui lòng mở một **Issue** trên GitHub và cung cấp:
- Phiên bản Blender bạn đang sử dụng.
- Loại mô hình thử nghiệm (ví dụ: Hunyuan 3D, Meshy, Tripo3D, Mixamo...).
- Nhật ký lỗi (error traceback) nếu có.
