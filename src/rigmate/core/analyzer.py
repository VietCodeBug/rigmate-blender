"""Logic phân tích chẩn đoán Rig và Mesh độc lập hoàn toàn với Blender."""

import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from rigmate.core.models import (
    MeshInfo,
    ArmatureInfo,
    BoneInfo,
    RigDiagnosticReport,
    DiagnosticIssue,
    FingerHeuristicSummary,
)


# Từ khóa heuristic nhận diện ngón tay (không áp đặt bắt buộc)
FINGER_PATTERNS = {
    "thumb": [r"thumb", r"polex", r"finger_1", r"ngon_cai", r"cai"],
    "index": [r"index", r"forefinger", r"finger_2", r"ngon_tro", r"tro"],
    "middle": [r"middle", r"finger_3", r"ngon_giua", r"giua"],
    "ring": [r"ring", r"finger_4", r"ngon_ap_ut", r"ap_ut"],
    "pinky": [r"pinky", r"little", r"finger_5", r"ngon_ut", r"ut"],
}

SIDE_PATTERNS = {
    "LEFT": [r"\.l$", r"_l$", r"\.left$", r"_left$", r"^left[_\.]", r"^l[_\.]"],
    "RIGHT": [r"\.r$", r"_r$", r"\.right$", r"_right$", r"^right[_\.]", r"^r[_\.]"],
}


class RigAnalyzer:
    """Bộ phân tích chẩn đoán cho workflow Tencent Hunyuan 3D + Meshy."""

    @classmethod
    def analyze(
        cls,
        mesh: Optional[MeshInfo] = None,
        armature: Optional[ArmatureInfo] = None,
    ) -> RigDiagnosticReport:
        now_str = datetime.now(timezone.utc).isoformat()
        issues: List[DiagnosticIssue] = []
        finger_summaries: List[FingerHeuristicSummary] = []

        # 1. Kiểm tra Mesh (Hunyuan 3D đặc thù ~50k đỉnh)
        if mesh:
            # Kiểm tra số lượng đỉnh đối với game engine Godot
            if mesh.vertex_count > 45000:
                issues.append(
                    DiagnosticIssue(
                        code="MESH_HIGH_POLY",
                        severity="WARNING",
                        title=f"Số lượng đỉnh cao ({mesh.vertex_count:,} đỉnh)",
                        message=(
                            "Mô hình Hunyuan 3D gốc thường có mật độ đỉnh dày (~50k đỉnh). "
                            "Mặc dù rig được trong Blender, số lượng đỉnh này có thể gây giảm hiệu năng khi xuất sang Godot. "
                            "Khuyến nghị: cân nhắc Decimate hoặc Remesh trước khi tạo shape key/anim hoàn chỉnh."
                        ),
                        target_object=mesh.name,
                        suggested_action="Dùng modifier Decimate hoặc Remesh nếu hướng tới game thời gian thực trong Godot.",
                    )
                )
            elif mesh.vertex_count > 0:
                issues.append(
                    DiagnosticIssue(
                        code="MESH_POLY_OK",
                        severity="INFO",
                        title=f"Số lượng đỉnh phù hợp ({mesh.vertex_count:,} đỉnh)",
                        message="Số lượng đỉnh mesh ở mức an toàn cho hiển thị và hoạt họa.",
                        target_object=mesh.name,
                    )
                )

            # Kiểm tra Transform mesh chưa apply
            if not mesh.transform.is_applied():
                issues.append(
                    DiagnosticIssue(
                        code="MESH_UNAPPLIED_TRANSFORM",
                        severity="WARNING",
                        title="Transform của Mesh chưa được áp dụng (Apply)",
                        message=(
                            f"Mesh '{mesh.name}' có Scale {mesh.transform.scale} hoặc Rotation khác chuẩn. "
                            "Điều này dễ gây méo mesh khi gắn xương hoặc xuất sang engine."
                        ),
                        target_object=mesh.name,
                        suggested_action="Thực hiện 'Apply All Transforms' (Ctrl+A trong Blender) trước khi bind xương.",
                    )
                )

            # Kiểm tra Armature modifier
            if not mesh.has_armature_modifier:
                issues.append(
                    DiagnosticIssue(
                        code="MESH_NO_ARMATURE_MODIFIER",
                        severity="WARNING",
                        title="Mesh chưa có Armature Modifier",
                        message=f"Mesh '{mesh.name}' chưa được liên kết với bộ xương nào qua Modifier.",
                        target_object=mesh.name,
                        suggested_action="Thêm Armature Modifier và chỉ định target armature.",
                    )
                )

        # 2. Kiểm tra Armature (Meshy hoặc rig nhập khẩu)
        if armature:
            # Kiểm tra Transform armature chưa apply
            if not armature.transform.is_applied():
                issues.append(
                    DiagnosticIssue(
                        code="ARMATURE_UNAPPLIED_TRANSFORM",
                        severity="WARNING",
                        title="Transform của Armature chưa được áp dụng (Apply)",
                        message=(
                            f"Bộ xương '{armature.name}' có Scale hoặc Rotation chưa áp dụng. "
                            "Khi xuất FBX/glTF sang Godot, xương có thể bị xoay lệch hoặc sai kích thước."
                        ),
                        target_object=armature.name,
                        suggested_action="Apply Transform cho Armature (Ctrl+A) ở Object Mode.",
                    )
                )

            # Kiểm tra số lượng bone
            if armature.total_bones == 0:
                issues.append(
                    DiagnosticIssue(
                        code="ARMATURE_EMPTY",
                        severity="ERROR",
                        title="Armature không có bone nào",
                        message=f"Bộ xương '{armature.name}' rỗng.",
                        target_object=armature.name,
                    )
                )
            else:
                # Phân tích các xương ngón tay theo heuristic
                finger_summaries = cls._detect_finger_heuristics(armature)

                # Cảnh báo dựa trên kết quả phát hiện ngón tay (dưới dạng gợi ý, không khẳng định sai sót)
                cls._evaluate_finger_diagnostic(finger_summaries, issues, armature.name)

        # 3. Đánh giá tương thích Godot sơ bộ
        error_count = sum(1 for i in issues if i.severity == "ERROR")
        warning_count = sum(1 for i in issues if i.severity == "WARNING")

        if error_count > 0:
            score = "CẦN SỬA"
        elif warning_count > 0:
            score = "CẦN LƯU Ý"
        else:
            score = "TỐT"

        summary_lines = [
            f"Đã hoàn thành phân tích chẩn đoán cho "
            f"Mesh: [{mesh.name if mesh else 'Không có'}] và Armature: [{armature.name if armature else 'Không có'}].",
            f"Tổng số phát hiện: {len(issues)} (Cảnh báo: {warning_count}, Lỗi: {error_count}).",
            f"Đánh giá sơ bộ xuất Godot: {score}.",
        ]

        return RigDiagnosticReport(
            timestamp=now_str,
            mesh_name=mesh.name if mesh else None,
            armature_name=armature.name if armature else None,
            issues=issues,
            finger_heuristics=finger_summaries,
            godot_compatibility_score=score,
            summary_text=" ".join(summary_lines),
        )

    @classmethod
    def _detect_finger_heuristics(cls, armature: ArmatureInfo) -> List[FingerHeuristicSummary]:
        """Nhận diện heuristic ngón tay dựa trên quy ước tên thông dụng của Meshy, Mixamo, Rigify."""
        left_detected: Dict[str, List[str]] = {k: [] for k in FINGER_PATTERNS}
        right_detected: Dict[str, List[str]] = {k: [] for k in FINGER_PATTERNS}
        unknown_detected: Dict[str, List[str]] = {k: [] for k in FINGER_PATTERNS}

        for bone_name in armature.bones.keys():
            lower_name = bone_name.lower()

            # Xác định bên trái / phải
            side = "UNKNOWN"
            for s_name, patterns in SIDE_PATTERNS.items():
                if any(re.search(p, lower_name) for p in patterns):
                    side = s_name
                    break

            # Kiểm tra khớp với ngón nào
            target_dict = left_detected if side == "LEFT" else (right_detected if side == "RIGHT" else unknown_detected)

            for finger_type, patterns in FINGER_PATTERNS.items():
                if any(re.search(p, lower_name) for p in patterns):
                    target_dict[finger_type].append(bone_name)

        summaries = []
        if any(bones for bones in left_detected.values()):
            summaries.append(
                FingerHeuristicSummary(
                    hand_side="LEFT",
                    detected_fingers={k: v for k, v in left_detected.items() if v},
                )
            )
        if any(bones for bones in right_detected.values()):
            summaries.append(
                FingerHeuristicSummary(
                    hand_side="RIGHT",
                    detected_fingers={k: v for k, v in right_detected.items() if v},
                )
            )
        if any(bones for bones in unknown_detected.values()):
            summaries.append(
                FingerHeuristicSummary(
                    hand_side="UNKNOWN",
                    detected_fingers={k: v for k, v in unknown_detected.items() if v},
                )
            )

        return summaries

    @classmethod
    def _evaluate_finger_diagnostic(
        cls,
        finger_summaries: List[FingerHeuristicSummary],
        issues: List[DiagnosticIssue],
        armature_name: str,
    ):
        """Đưa ra nhận xét gợi ý về ngón tay. Lưu ý: Tên xương chỉ là gợi ý, KHÔNG khẳng định thiếu ngón."""
        expected_fingers = ["thumb", "index", "middle", "ring", "pinky"]

        if not finger_summaries:
            issues.append(
                DiagnosticIssue(
                    code="FINGERS_NOT_DETECTED_BY_NAME",
                    severity="SUGGESTION",
                    title="Chưa phát hiện xương ngón tay theo quy ước tên phổ biến",
                    message=(
                        "Không tìm thấy tên xương ngón tay thông thường (thumb, index, finger_...). "
                        "Đây là trường hợp bình thường nếu mô hình Meshy tạo rig đơn giản dạng bàn tay nắm (mitten hand) "
                        "hoặc mô hình Hunyuan 3D có bàn tay dính liền. Tên xương chỉ là gợi ý, không khẳng định mô hình bị thiếu ngón. "
                        "Ghi chú: RigMate sẽ hỗ trợ công cụ bổ sung xương ngón tay trong các bản cập nhật tiếp theo."
                    ),
                    target_object=armature_name,
                    suggested_action="Nếu nhân vật cần cử động ngón, có thể dùng công cụ RigMate để thêm chuỗi xương ngón.",
                )
            )
            return

        for summary in finger_summaries:
            detected_types = list(summary.detected_fingers.keys())
            missing_types = [f for f in expected_fingers if f not in detected_types]

            if missing_types:
                side_vn = "Tay trái" if summary.hand_side == "LEFT" else ("Tay phải" if summary.hand_side == "RIGHT" else "Bàn tay")
                issues.append(
                    DiagnosticIssue(
                        code="FINGERS_PARTIAL_HEURISTIC",
                        severity="SUGGESTION",
                        title=f"Gợi ý cấu trúc ngón ({side_vn}): Phát hiện {len(detected_types)}/5 loại ngón theo tên",
                        message=(
                            f"Nhận diện được: {', '.join(detected_types)}. Chưa khớp từ khóa cho: {', '.join(missing_types)}. "
                            "Lưu ý: Tên xương chỉ mang tính gợi ý, không khẳng định mô hình bị thiếu ngón nếu rig dùng quy ước riêng."
                        ),
                        target_object=armature_name,
                    )
                )
            else:
                side_vn = "Tay trái" if summary.hand_side == "LEFT" else ("Tay phải" if summary.hand_side == "RIGHT" else "Bàn tay")
                issues.append(
                    DiagnosticIssue(
                        code="FINGERS_COMPLETE_HEURISTIC",
                        severity="INFO",
                        title=f"Cấu trúc ngón ({side_vn}): Khớp đủ 5 nhóm ngón theo tên chuẩn",
                        message=f"Đã phát hiện đầy đủ các chuỗi xương cho 5 ngón ({side_vn}).",
                        target_object=armature_name,
                    )
                )
