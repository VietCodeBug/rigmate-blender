"""Diagnostic analysis logic for Rig and Mesh decoupled completely from Blender."""

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
from rigmate.core.i18n import t


# Heuristic patterns for finger identification (non-dogmatic)
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
    """Diagnostic analyzer tailored for Tencent Hunyuan 3D + Meshy workflow."""

    @classmethod
    def analyze(
        cls,
        mesh: Optional[MeshInfo] = None,
        armature: Optional[ArmatureInfo] = None,
        locale: Optional[str] = None,
    ) -> RigDiagnosticReport:
        now_str = datetime.now(timezone.utc).isoformat()
        issues: List[DiagnosticIssue] = []
        finger_summaries: List[FingerHeuristicSummary] = []

        # 1. Mesh inspection (Hunyuan 3D characteristics ~50k vertices)
        if mesh:
            if mesh.vertex_count > 45000:
                issues.append(
                    DiagnosticIssue(
                        code="MESH_HIGH_POLY",
                        severity="WARNING",
                        title=t("diag.high_poly_title", locale=locale, count=mesh.vertex_count),
                        message=t("diag.high_poly_msg", locale=locale),
                        target_object=mesh.name,
                        suggested_action=t("diag.high_poly_action", locale=locale),
                    )
                )
            elif mesh.vertex_count > 0:
                issues.append(
                    DiagnosticIssue(
                        code="MESH_POLY_OK",
                        severity="INFO",
                        title=t("diag.poly_ok_title", locale=locale, count=mesh.vertex_count),
                        message=t("diag.poly_ok_msg", locale=locale),
                        target_object=mesh.name,
                    )
                )

            # Check unapplied transforms
            if not mesh.transform.is_applied():
                issues.append(
                    DiagnosticIssue(
                        code="MESH_UNAPPLIED_TRANSFORM",
                        severity="WARNING",
                        title=t("diag.mesh_unapplied_transform_title", locale=locale),
                        message=t("diag.mesh_unapplied_transform_msg", locale=locale, name=mesh.name),
                        target_object=mesh.name,
                        suggested_action=t("diag.mesh_unapplied_transform_action", locale=locale),
                    )
                )

            # Check armature modifier
            if not mesh.has_armature_modifier:
                issues.append(
                    DiagnosticIssue(
                        code="MESH_NO_ARMATURE_MODIFIER",
                        severity="WARNING",
                        title=t("diag.no_armature_mod_title", locale=locale),
                        message=t("diag.no_armature_mod_msg", locale=locale, name=mesh.name),
                        target_object=mesh.name,
                        suggested_action=t("diag.no_armature_mod_action", locale=locale),
                    )
                )

        # 2. Armature inspection (Meshy or imported rig)
        if armature:
            if not armature.transform.is_applied():
                issues.append(
                    DiagnosticIssue(
                        code="ARMATURE_UNAPPLIED_TRANSFORM",
                        severity="WARNING",
                        title=t("diag.armature_unapplied_transform_title", locale=locale),
                        message=t("diag.armature_unapplied_transform_msg", locale=locale, name=armature.name),
                        target_object=armature.name,
                        suggested_action=t("diag.armature_unapplied_transform_action", locale=locale),
                    )
                )

            if armature.total_bones == 0:
                issues.append(
                    DiagnosticIssue(
                        code="ARMATURE_EMPTY",
                        severity="ERROR",
                        title=t("diag.armature_empty_title", locale=locale),
                        message=t("diag.armature_empty_msg", locale=locale, name=armature.name),
                        target_object=armature.name,
                    )
                )
            else:
                finger_summaries = cls._detect_finger_heuristics(armature)
                cls._evaluate_finger_diagnostic(finger_summaries, issues, armature.name, locale=locale)

        # 3. Godot compatibility score
        error_count = sum(1 for i in issues if i.severity == "ERROR")
        warning_count = sum(1 for i in issues if i.severity == "WARNING")

        if error_count > 0:
            score = t("diag.score_fix", locale=locale)
        elif warning_count > 0:
            score = t("diag.score_caution", locale=locale)
        else:
            score = t("diag.score_good", locale=locale)

        summary_text = t(
            "diag.summary",
            locale=locale,
            mesh=mesh.name if mesh else "None",
            armature=armature.name if armature else "None",
            count=len(issues),
            warnings=warning_count,
            errors=error_count,
            score=score,
        )

        return RigDiagnosticReport(
            timestamp=now_str,
            mesh_name=mesh.name if mesh else None,
            armature_name=armature.name if armature else None,
            issues=issues,
            finger_heuristics=finger_summaries,
            godot_compatibility_score=score,
            summary_text=summary_text,
        )

    @classmethod
    def _detect_finger_heuristics(cls, armature: ArmatureInfo) -> List[FingerHeuristicSummary]:
        """Detect finger bone chains using heuristic conventions (Meshy, Mixamo, Rigify)."""
        left_detected: Dict[str, List[str]] = {k: [] for k in FINGER_PATTERNS}
        right_detected: Dict[str, List[str]] = {k: [] for k in FINGER_PATTERNS}
        unknown_detected: Dict[str, List[str]] = {k: [] for k in FINGER_PATTERNS}

        for bone_name in armature.bones.keys():
            lower_name = bone_name.lower()

            side = "UNKNOWN"
            for s_name, patterns in SIDE_PATTERNS.items():
                if any(re.search(p, lower_name) for p in patterns):
                    side = s_name
                    break

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
        locale: Optional[str] = None,
    ):
        """Provide heuristic feedback on fingers. Names are suggestions, not strict confirmations."""
        expected_fingers = ["thumb", "index", "middle", "ring", "pinky"]

        if not finger_summaries:
            issues.append(
                DiagnosticIssue(
                    code="FINGERS_NOT_DETECTED_BY_NAME",
                    severity="SUGGESTION",
                    title=t("diag.finger_not_detected_title", locale=locale),
                    message=t("diag.finger_not_detected_msg", locale=locale),
                    target_object=armature_name,
                    suggested_action=t("diag.finger_not_detected_action", locale=locale),
                )
            )
            return

        for summary in finger_summaries:
            detected_types = list(summary.detected_fingers.keys())
            missing_types = [f for f in expected_fingers if f not in detected_types]

            side_label = (
                t("side.left", locale=locale)
                if summary.hand_side == "LEFT"
                else (t("side.right", locale=locale) if summary.hand_side == "RIGHT" else t("side.hand", locale=locale))
            )

            if missing_types:
                issues.append(
                    DiagnosticIssue(
                        code="FINGERS_PARTIAL_HEURISTIC",
                        severity="SUGGESTION",
                        title=t("diag.finger_partial_title", locale=locale, side=side_label, count=len(detected_types)),
                        message=t(
                            "diag.finger_partial_msg",
                            locale=locale,
                            detected=", ".join(detected_types),
                            missing=", ".join(missing_types),
                        ),
                        target_object=armature_name,
                    )
                )
            else:
                issues.append(
                    DiagnosticIssue(
                        code="FINGERS_COMPLETE_HEURISTIC",
                        severity="INFO",
                        title=t("diag.finger_complete_title", locale=locale, side=side_label),
                        message=t("diag.finger_complete_msg", locale=locale, side=side_label),
                        target_object=armature_name,
                    )
                )
