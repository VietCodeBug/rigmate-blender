"""Kiểm thử bộ phân tích chẩn đoán Rig và Mesh (đặc thù Hunyuan 3D + Meshy + Godot)."""

import pytest
from rigmate.core.analyzer import RigAnalyzer
from rigmate.core.models import (
    MeshInfo,
    ArmatureInfo,
    BoneInfo,
    TransformData,
)


def test_analyzer_hunyuan_high_poly_warning():
    # Mô hình Hunyuan 3D có 55,000 đỉnh
    mesh = MeshInfo(
        name="HunyuanCharacter",
        vertex_count=55000,
        polygon_count=55000,
        has_armature_modifier=True,
    )
    report = RigAnalyzer.analyze(mesh=mesh)

    assert any(i.code == "MESH_HIGH_POLY" for i in report.issues)
    assert report.godot_compatibility_score in ["CẦN LƯU Ý", "CẦN SỬA"]


def test_analyzer_unapplied_transforms():
    mesh = MeshInfo(
        name="BadTransformMesh",
        vertex_count=10000,
        transform=TransformData(scale=[1.5, 1.5, 1.5]),
    )
    armature = ArmatureInfo(
        name="BadTransformArmature",
        total_bones=10,
        transform=TransformData(rotation_euler=[0.5, 0.0, 0.0]),
    )
    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)

    assert any(i.code == "MESH_UNAPPLIED_TRANSFORM" for i in report.issues)
    assert any(i.code == "ARMATURE_UNAPPLIED_TRANSFORM" for i in report.issues)


def test_analyzer_finger_heuristics_non_dogmatic():
    # Trường hợp 1: Rig Meshy dạng bàn tay nắm (chỉ có Hand.L, Hand.R)
    armature_mitten = ArmatureInfo(
        name="MeshyMittenRig",
        bones={
            "Hips": BoneInfo(name="Hips"),
            "Hand.L": BoneInfo(name="Hand.L"),
            "Hand.R": BoneInfo(name="Hand.R"),
        },
        total_bones=3,
    )
    report_mitten = RigAnalyzer.analyze(armature=armature_mitten)

    # KHÔNG được coi là ERROR mà là SUGGESTION (gợi ý), không khẳng định sai sót
    issue = next((i for i in report_mitten.issues if i.code == "FINGERS_NOT_DETECTED_BY_NAME"), None)
    assert issue is not None
    assert issue.severity == "SUGGESTION"
    assert "không khẳng định" in issue.message.lower()

    # Trường hợp 2: Rig có đủ 5 ngón tay chuẩn
    bones_full = {"Hips": BoneInfo(name="Hips")}
    for f in ["thumb", "index", "middle", "ring", "pinky"]:
        bones_full[f"{f}_01.l"] = BoneInfo(name=f"{f}_01.l")

    armature_full = ArmatureInfo(
        name="FullRig",
        bones=bones_full,
        total_bones=len(bones_full),
    )
    report_full = RigAnalyzer.analyze(armature=armature_full)
    assert any(i.code == "FINGERS_COMPLETE_HEURISTIC" for i in report_full.issues)
