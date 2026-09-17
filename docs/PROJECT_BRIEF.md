# BẢN TÓM TẮT DỰ ÁN RIGMATE (PROJECT BRIEF)

## 1. Tầm Nhìn Sản Phẩm
**RigMate** là trợ lý AI mã nguồn mở tích hợp trực tiếp bên trong Blender, sinh ra nhằm giải phóng người sáng tạo nội dung, nghệ sĩ độc lập (indie game developer), và người dùng ít kiến thức 3D khỏi sự phức tạp của kỹ thuật rigging và animation setup.

## 2. Quy Trình Thực Tế (Target Pipeline)
1. **Tạo mô hình AI**: Người dùng sinh mesh 3D từ các công cụ tạo sinh (tiêu biểu là **Tencent Hunyuan 3D**). Mô hình thường có mật độ đỉnh dày (~50.000 đỉnh) và bàn tay dính liền hoặc dạng bàn tay nắm.
2. **Auto-Rigging cơ bản**: Mô hình được chuyển qua **Meshy** (hoặc Tripo/Mixamo) để tự động tạo khung xương cơ bản.
3. **Nhập vào Blender**: Người dùng mở file trong Blender.
4. **Đồng hành cùng RigMate**:
   - Chẩn đoán sơ bộ các lỗi phổ biến (Transform chưa apply, scale lệch, thừa đỉnh đối với game engine).
   - Nhận diện heuristic cấu trúc ngón tay (không khẳng định sai sót chỉ vì tên xương khác quy ước).
   - Hỗ trợ các bước tinh chỉnh xương bàn tay, chuẩn bị weight painting và kiểm tra tư thế.
5. **Đích đến**: Xuất nhân vật hoạt họa hoàn chỉnh sang **Godot Engine** (định dạng glTF 2.0 / .glb).

## 3. Định Vị Kỹ Thuật
- **Không phải AI tạo model từ đầu**: RigMate không tạo mesh từ text prompt, mà hỗ trợ kiểm tra, chẩn đoán và chỉnh sửa nhân vật có sẵn trong Blender.
- **Không đánh giá topology thuần túy qua số đỉnh**: Số lượng đỉnh dày (~50k) được cảnh báo về mặt hiệu năng game engine thời gian thực, không đồng nhất với việc mô hình bị lỗi mesh.
- **Tương tác đàm thoại tự nhiên kết hợp công cụ MCP**: Người dùng ra lệnh bằng ngôn ngữ tự nhiên ngay trong tab Sidebar của Blender; hệ thống AI phân tích và điều phối các công cụ thao tác Blender một cách an toàn.
