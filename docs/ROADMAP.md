# Lộ Trình Phát Triển RigMate (Roadmap)

Dự án tuân thủ nguyên tắc: **Không trình bày tính năng chưa có như đã hoàn thành**. Dưới đây là phân kỳ phát triển minh bạch:

---

## Phiên bản v0.1 (Hiện tại - Nền tảng & Chẩn đoán)
- [x] Khung kiến trúc chia module rõ ràng (`contracts`, `analysis`, `localization`, `core`, `storage`, `providers`, `bridge`, `mcp_server`, `blender_addon`).
- [x] Độc lập hoàn toàn với `bpy` ở tầng core, contracts, và storage (chạy 166 unit test không cần Blender).
- [x] Kiểm chứng khôi phục sau sự cố bằng tiến trình con thực tế (`subprocess` Phase A/B, PID độc lập, khôi phục ACK loss).
- [x] Chẩn đoán sơ bộ mô hình Tencent Hunyuan 3D (~50k đỉnh) và Armature Meshy.
- [x] Nhận diện xương ngón tay theo heuristic không áp đặt (non-dogmatic finger detection).
- [x] Hệ thống Thanh Năng Lượng và Quota minh bạch (phân biệt `[Tự động]`, `[Nhập thủ công]`, `[DEMO]`).
- [x] Quản lý phiên hội thoại, lưu trữ nguyên tử (Atomic write), chống hỏng file, hỗ trợ Unicode tiếng Việt.
- [x] Hợp đồng công cụ MCP cơ bản (`inspect_scene`, `inspect_mesh`, `inspect_armature`, `diagnose_rig`).
- [x] Giao diện Blender Add-on Sidebar tab với thanh năng lượng, nút gửi/hủy, chẩn đoán nhanh.
- [x] Script đóng gói ZIP tự động với danh sách cho phép nghiêm ngặt (không kéo theo Pydantic/FastAPI).
- [x] Hoàn thiện đặc tả kiến trúc Mô-đun **Kiểm tra & sửa lưới (Mesh Preparation)** (`docs/modules/mesh_preparation.md`).

---

## Phân kỳ phát triển Mô-đun "Kiểm tra & sửa lưới" (Mesh Preparation Delivery Phases)

### Phase A — Kiểm tra hình học chỉ đọc (Read-Only Mesh Inspection - Ưu tiên 1)
- [ ] **Hợp đồng công cụ `mesh.inspect` & `mesh.analyze`**:
  - Trích xuất thống kê hình học: số đỉnh, cạnh, mặt, số tam giác sau khi triangulate.
  - Phân tích cấu trúc: Non-manifold edges, loose vertices, degenerate faces, near-duplicate vertices (ngưỡng tương đối theo tỷ lệ model), đảo vector pháp tuyến (inverted normals).
  - Kiểm tra UV & vật liệu: Sự tồn tại của UV map, vật liệu, tham chiếu texture bị thiếu, phân biệt UV lật đối xứng hợp lệ.
  - Kiểm tra biến dạng: Armature modifier, vertex groups, đỉnh chưa gán trọng số, đỉnh vượt quá 4 xương ảnh hưởng cho Godot.
  - Đánh giá theo mục đích sử dụng (Contextual severity: `STATIC_OBJECT`, `ANIMATED_CHARACTER`, `GODOT_EXPORT_PREPARATION`).
  - Toàn bộ logic chạy độc lập kiểm thử không cần Blender (Headless unit tests với 16 bộ test fixtures).

### Phase B — Sửa lỗi có kiểm soát & Bản sao thử nghiệm (Controlled Cleanup - Ưu tiên 2)
- [ ] **Quy trình Preview an toàn trên bản sao**:
  - `mesh.preview_repair`: Thực hiện chỉnh sửa trên đối tượng tạm thời (`_preview`), không chạm vào asset gốc.
  - Đo lường so sánh trước/sau (`mesh.compare`): Biến thiên số lượng đa giác, độ trôi UV, thể tích bao quát.
- [ ] **Các thao tác dọn dẹp cơ bản (Scoped Cleanup)**:
  - Xóa đỉnh/cạnh lơ lửng (loose geometry).
  - Tự động sửa mặt suy biến (degenerate faces).
  - Đảo lại vector pháp tuyến bị lật (recalculate normals).
  - Vá lỗ thủng biên nhỏ có kiểm soát.
  - Bắt buộc Checkpoint và Document Writer Lock trước khi thực thi `mesh.apply_repair`.

### Phase C — Tinh chỉnh Bàn tay & Ngón tay nhân vật (Character Hand/Finger Remediation - Ưu tiên 3)
- [ ] **Quy trình chuyên sâu 10 bước cho bàn tay Hunyuan/Meshy**:
  - Phát hiện vùng bàn tay tự động; yêu cầu người dùng xác nhận mốc giải phẫu (wrist, palm, fingertips) khi độ tin cậy $< 85\%$ (`NEEDS_INPUT`).
  - Phân loại rõ ràng 7 dạng lỗi bàn tay (ngón tay chạm gần trực quan vs dính lưới vật lý vs rò rỉ trọng số xương).
  - Tùy biến số lượng ngón tay (hỗ trợ nhân vật hoạt hình 3 hoặc 4 ngón, tránh cảnh báo sai).
  - Thử nghiệm tư thế không phá hủy (`deformation.run_pose_checks`): duỗi thẳng, gập ngón, nắm đấm, kẹp ngón, cầm vật thể; đảm bảo khôi phục 100% rest pose.

### Phase D — Tái tạo lưới cục bộ & Chuyển giao dữ liệu (Advanced Local Topology - Ưu tiên 4)
- [ ] **Local Retopology & Data Transfer**:
  - Tái tạo dòng lưới cục bộ tại các khớp nối (elbows, knees) hoặc tách ngón tay dính.
  - Động cơ chuyển giao trọng số (weight transfer) và ánh xạ lại tọa độ UV.
  - Đánh giá sai lệch bề mặt (surface deviation metrics).

### Phase E — Nghiên cứu Tự động Retopology toàn diện (Broad Retopology Research - Ưu tiên 5)
- [ ] **Nghiên cứu Quad Retopology toàn thân**:
  - Đánh giá các thư viện thuật toán mã nguồn mở tương thích bản quyền GPL.
  - Xây dựng bộ công cụ benchmark so sánh chất lượng hình học và khả năng giữ chi tiết.

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

