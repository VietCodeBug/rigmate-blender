"""Tests for Rig and Mesh diagnostic analyzer (Hunyuan 3D + Meshy + Godot pipeline)."""

import pytest
from rigmate.core.analyzer import RigAnalyzer
from rigmate.core.models import (
    MeshInfo,
    ArmatureInfo,
    BoneInfo,
    TransformData,
)
from rigmate.core.i18n import set_locale


def test_analyzer_hunyuan_high_poly_warning():
    # Hunyuan 3D model with 55,000 vertices
    mesh = MeshInfo(
        name="HunyuanCharacter",
        vertex_count=55000,
        polygon_count=55000,
        has_armature_modifier=True,
    )
    report = RigAnalyzer.analyze(mesh=mesh)

    assert any(i.code == "MESH_HIGH_POLY" for i in report.issues)
    assert report.godot_compatibility_score in ["NEEDS ATTENTION", "NEEDS FIX"]

    # Test Vietnamese localized output
    set_locale("vi")
    report_vi = RigAnalyzer.analyze(mesh=mesh)
    assert report_vi.godot_compatibility_score in ["CẦN LƯU Ý", "CẦN SỬA"]
    set_locale("en")


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
    # Case 1: Meshy mitten hand rig (only Hand.L, Hand.R)
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

    # Must NOT be ERROR, must be SUGGESTION, non-dogmatic heuristic
    issue = next((i for i in report_mitten.issues if i.code == "FINGERS_NOT_DETECTED_BY_NAME"), None)
    assert issue is not None
    assert issue.severity == "SUGGESTION"
    assert "heuristic suggestions" in issue.message.lower()

    # Case 2: Full 5 fingers detected
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

