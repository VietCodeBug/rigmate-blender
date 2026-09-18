"""Tests for character inspection fixtures and deterministic diagnostic analysis."""

import json
from pathlib import Path
import pytest

from rigmate.blender_addon.analyzer import RigAnalyzer
from rigmate.blender_addon.dto import ArmatureInfo, BoneInfo, MeshInfo, TransformData, VertexWeightSummary


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "characters"


def _load_fixture(name: str):
    path = FIXTURES_DIR / f"{name}.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mesh = None
    if data.get("mesh"):
        m = data["mesh"]
        t_data = m.get("transform", {})
        trans = TransformData(
            location=t_data.get("location", [0.0, 0.0, 0.0]),
            rotation_euler=t_data.get("rotation_euler", [0.0, 0.0, 0.0]),
            scale=t_data.get("scale", [1.0, 1.0, 1.0]),
        )
        ws_data = m.get("weights_summary")
        ws = None
        if ws_data:
            ws = VertexWeightSummary(
                unweighted_vertex_count=ws_data.get("unweighted_vertex_count", 0),
                max_weights_per_vertex=ws_data.get("max_weights_per_vertex", 0),
                exceeds_godot_max_weights=ws_data.get("exceeds_godot_max_weights", False),
            )
        mesh = MeshInfo(
            name=m["name"],
            vertex_count=m.get("vertex_count", 0),
            edge_count=m.get("edge_count", 0),
            polygon_count=m.get("polygon_count", 0),
            has_armature_modifier=m.get("has_armature_modifier", False),
            target_armature_name=m.get("target_armature_name"),
            transform=trans,
            vertex_groups=m.get("vertex_groups", []),
            weights_summary=ws,
            materials_count=m.get("materials_count", 0),
        )

    armature = None
    if data.get("armature"):
        a = data["armature"]
        t_data = a.get("transform", {})
        trans = TransformData(
            location=t_data.get("location", [0.0, 0.0, 0.0]),
            rotation_euler=t_data.get("rotation_euler", [0.0, 0.0, 0.0]),
            scale=t_data.get("scale", [1.0, 1.0, 1.0]),
        )
        bones = {}
        for b_name, b_data in a.get("bones", {}).items():
            bones[b_name] = BoneInfo(
                name=b_data.get("name", b_name),
                parent_name=b_data.get("parent_name"),
                children_names=b_data.get("children_names", []),
                head=b_data.get("head", [0.0, 0.0, 0.0]),
                tail=b_data.get("tail", [0.0, 0.0, 0.0]),
                length=b_data.get("length", 0.0),
                connected=b_data.get("connected", False),
                use_deform=b_data.get("use_deform", True),
            )
        armature = ArmatureInfo(
            name=a["name"],
            bones=bones,
            root_bone_names=a.get("root_bone_names", []),
            transform=trans,
            total_bones=a.get("total_bones", len(bones)),
            deform_bones_count=a.get("deform_bones_count", len(bones)),
        )

    return mesh, armature


def test_fixture_basic_mesh_diagnostics():
    """basic_mesh.json has high poly and lacks armature modifier."""
    mesh, armature = _load_fixture("basic_mesh")
    assert mesh is not None
    assert armature is None

    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
    issue_codes = [issue.code for issue in report.issues]
    assert "MESH_NO_ARMATURE_MODIFIER" in issue_codes
    assert "MESH_HIGH_POLY" in issue_codes
    assert report.ready_for_godot is False


def test_fixture_mesh_with_armature_clean():
    """mesh_with_armature.json has proper modifier, clean poly, and applied transforms."""
    mesh, armature = _load_fixture("mesh_with_armature")
    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
    issue_codes = [issue.code for issue in report.issues]
    assert "MESH_NO_ARMATURE_MODIFIER" not in issue_codes
    assert "MESH_UNAPPLIED_TRANSFORM" not in issue_codes
    assert "ARMATURE_UNAPPLIED_TRANSFORM" not in issue_codes
    assert "MESH_POLY_OK" in issue_codes


def test_fixture_meshy_style_rig_complete_fingers():
    """meshy_style_rig.json matches all 5 fingers for left and right hands."""
    mesh, armature = _load_fixture("meshy_style_rig")
    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
    issue_codes = [issue.code for issue in report.issues]
    assert "FINGERS_COMPLETE_HEURISTIC" in issue_codes
    assert len(report.finger_heuristics) >= 2


def test_fixture_missing_finger_chain():
    """missing_finger_chain.json detects partial finger chain (thumb/index only)."""
    mesh, armature = _load_fixture("missing_finger_chain")
    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
    issue_codes = [issue.code for issue in report.issues]
    assert "FINGERS_PARTIAL_HEURISTIC" in issue_codes


def test_fixture_excessive_weights_detected():
    """excessive_weights.json detects unweighted vertices and >4 max influences."""
    mesh, armature = _load_fixture("excessive_weights")
    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
    issue_codes = [issue.code for issue in report.issues]
    assert "WEIGHTS_UNWEIGHTED_VERTICES" in issue_codes
    assert "WEIGHTS_EXCEED_LIMIT" in issue_codes


def test_fixture_unapplied_transform_detected():
    """unapplied_transform.json detects unapplied transforms on both mesh and armature."""
    mesh, armature = _load_fixture("unapplied_transform")
    report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
    issue_codes = [issue.code for issue in report.issues]
    assert "MESH_UNAPPLIED_TRANSFORM" in issue_codes
    assert "ARMATURE_UNAPPLIED_TRANSFORM" in issue_codes
