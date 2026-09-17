# Lộ Trình Phát Triển RigMate (Roadmap)

Dự án tuân thủ nguyên tắc: **Không trình bày tính năng chưa có như đã hoàn thành**. Dưới đây là phân kỳ phát triển minh bạch:

---

## Phiên bản v0.1 (Hiện tại - Nền tảng & Chẩn đoán)
- [x] Khung kiến trúc chia module rõ ràng (`core`, `storage`, `providers`, `bridge`, `mcp_server`, `blender_addon`).
- [x] Độc lập hoàn toàn với `bpy` ở tầng core và storage (chạy unit test không cần Blender).
- [x] Chẩn đoán sơ bộ mô hình Tencent Hunyuan 3D (~50k đỉnh) và Armature Meshy.
- [x] Nhận diện xương ngón tay theo heuristic không áp đặt (non-dogmatic finger detection).
- [x] Hệ thống Thanh Năng Lượng và Quota minh bạch (phân biệt `[Tự động]`, `[Nhập thủ công]`, `[DEMO]`).
- [x] Quản lý phiên hội thoại, lưu trữ nguyên tử (Atomic write), chống hỏng file, hỗ trợ Unicode tiếng Việt.
- [x] Hợp đồng 4 công cụ MCP cơ bản (`inspect_scene`, `inspect_mesh`, `inspect_armature`, `diagnose_rig`).
- [x] Giao diện Blender Add-on Sidebar tab với thanh năng lượng, nút gửi/hủy, chẩn đoán nhanh.
- [x] Script đóng gói ZIP tự động và kịch bản demo CLI.

---

## Phiên bản v0.2 (Tương tác Tinh chỉnh & Thêm Xương Ngón Tay)
- [ ] **Bộ sinh xương ngón tay tự động (Auto Finger Bones)**:
  - Cho phép người dùng chọn bàn tay (dạng bàn tay nắm hoặc dính ngón của Hunyuan 3D).
  - Tự động sinh chuỗi 5 xương ngón tay dựa trên tỷ lệ bàn tay và gắn vào xương cổ tay (Wrist/Hand bone) của Meshy.
- [ ] **Công cụ sửa lỗi Mesh cơ bản**:
  - Tích hợp phím tắt/operator hỗ trợ Apply Transforms, Recalculate Normals, và Decimate an toàn giữ nguyên UV.
- [ ] **Kết nối tự động Antigravity CLI**:
  - Tự động đồng bộ với phiên đăng nhập `agy` trên máy người dùng tại nhà mà không cần cấu hình thủ công.

---

## Phiên bản v0.3 (Chỉnh Trọng Số & Thử Tư Thế)
- [ ] **Weight Painting Assistant**:
  - Hỗ trợ AI phân tích vùng biến dạng (deform issues) và tự động gán trọng số tự động (Smooth weights, Limit Total 4-weights cho Godot).
- [ ] **Pose Tester**:
  - Thư viện các tư thế cơ bản (T-pose, A-pose, nắm tay, bước đi, nhảy) để người dùng kiểm tra nhanh độ biến dạng của lưới trước khi xuất.

---

## Phiên bản v1.0 (Xuất Hoàn Thiện Cho Godot Engine)
- [ ] **Godot Export One-Click**:
  - Xuất trực tiếp sang định dạng `.glb` tối ưu hóa hoặc `.tscn` scene tương thích hoàn hảo với AnimationPlayer / AnimationTree của Godot 4.x.
- [ ] **Phân tích Ragdoll & Collision Shapes**:
  - Tự động sinh PhysicalBone3D và hộp va chạm chuẩn kích thước nhân vật.
