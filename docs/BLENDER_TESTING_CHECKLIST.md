# Checklist Kiểm Thử Trên Blender Thật (Real Blender Testing Checklist)

Tài liệu này cung cấp danh sách kiểm tra từng bước khi bạn thử nghiệm trực tiếp trên môi trường Blender tại nhà.

> **Lưu ý quan trọng:**
> Kết quả chạy thử nghiệm bằng **Mock Provider** trên máy công ty chỉ chứng minh tính đúng đắn của kiến trúc logic. Nó **không phải là bằng chứng** cho thấy Blender thật hoặc Antigravity CLI thật đã hoạt động hoàn hảo. Cần hoàn thành checklist dưới đây trên máy thật.

---

## 1. Kiểm Thử Cài Đặt Add-on
- [ ] Add-on cài đặt thành công từ file `.zip` mà không phát sinh lỗi cảnh báo (error trace).
- [ ] Add-on xuất hiện đúng vị trí: `View3D > Sidebar (phím N) > Tab RigMate`.
- [ ] Khi tắt và mở lại Blender, Add-on vẫn giữ nguyên trạng thái kích hoạt.

## 2. Kiểm Thử Giao Tiếp Bridge & Không Đơ Giao Diện
- [ ] Khi Bridge Server chưa chạy: Nhấn "Kiểm tra" hiển thị cảnh báo nhẹ nhàng, Blender không bị treo.
- [ ] Khi Bridge Server đã bật: Nhấn "Kiểm tra" chuyển trạng thái sang "Đã kết nối".
- [ ] Khi gửi tin nhắn dài hoặc mạng có độ trễ: Viewport 3D vẫn xoay, zoom và tương tác bình thường trong lúc chờ AI phản hồi (Background threading hoạt động đúng).
- [ ] Nhấn nút "Dừng lại" khi AI đang sinh chữ: Tác vụ dừng ngay lập tức, không làm crash Blender.

## 3. Kiểm Thử Dữ Liệu Nhân Vật Hunyuan 3D + Meshy
- [ ] Import file mô hình từ Hunyuan 3D (định dạng `.obj` hoặc `.fbx`).
- [ ] Bấm nút "Chẩn đoán nhanh Scene/Rig":
  - [ ] Hiển thị chính xác số lượng đỉnh của Mesh (khoảng ~50.000 đỉnh).
  - [ ] Phát hiện đúng cảnh báo nếu Mesh chưa Apply Transforms (Scale khác 1.0).
- [ ] Import bộ xương từ Meshy:
  - [ ] Đọc đúng danh sách bone và phân cấp cha-con.
  - [ ] Nếu bàn tay Meshy không chia 5 ngón, kiểm tra xem chẩn đoán có đưa ra dạng `[SUGGESTION]` nhẹ nhàng hay không (đảm bảo không báo lỗi vô lý).

## 4. Kiểm Thử Thanh Năng Lượng & Quota
- [ ] Nếu dùng Mock: Hiển thị rõ nhãn `[DEMO]`, thanh slider năng lượng thể hiện đúng tỷ lệ %.
- [ ] Nếu dùng Antigravity chưa có API: Hiển thị dòng chữ `Chưa đọc được hạn mức tự động`.
- [ ] Thử mở popup "Cập nhật Quota thủ công":
  - [ ] Nhập số hạn mức còn lại và tổng hạn mức.
  - [ ] Kiểm tra thanh năng lượng có cập nhật tỷ lệ % và ghi nhãn `[Nhập thủ công]` hay không.
  - [ ] Đóng và mở lại Blender, kiểm tra snapshot thủ công có còn lưu trong AppData hay không.

## 5. Kiểm Thử Lưu Trữ & Unicode Tiếng Việt
- [ ] Chat bằng tiếng Việt có dấu đầy đủ (ví dụ: "Kiểm tra xương cánh tay trái và ngón cái").
- [ ] Kiểm tra chữ tiếng Việt hiển thị sắc nét, không bị lỗi font hoặc ký tự `\uXXXX`.
- [ ] Tạo phiên chat mới bằng nút "Mới": Lịch sử tin nhắn được làm sạch và phiên cũ được lưu vào file JSON cục bộ.
