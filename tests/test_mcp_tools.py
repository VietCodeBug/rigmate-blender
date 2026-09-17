"""Kiểm thử hợp đồng công cụ MCP (inspect_scene, inspect_mesh, inspect_armature, diagnose_rig)."""

import json
from rigmate.mcp_server.tools import RigMateMCPTools
from rigmate.mcp_server.server import (
    inspect_scene,
    inspect_mesh,
    inspect_armature,
    diagnose_rig,
)


def test_mcp_tools_contract():
    tools = RigMateMCPTools()

    # 1. Test inspect_scene
    scene_payload = {
        "active_object_name": "Hero_Mesh",
        "selected_object_names": ["Hero_Mesh"],
        "objects": [
            {"name": "Hero_Mesh", "type": "MESH", "is_selected": True, "is_active": True}
        ],
    }
    res_scene = tools.inspect_scene(scene_payload)
    assert res_scene["active_object_name"] == "Hero_Mesh"

    # 2. Test inspect_mesh
    mesh_payload = {
        "name": "Hero_Mesh",
        "vertex_count": 51000,
        "edge_count": 102000,
        "polygon_count": 51000,
        "has_armature_modifier": True,
    }
    res_mesh = tools.inspect_mesh(mesh_payload)
    assert res_mesh["vertex_count"] == 51000

    # 3. Test inspect_armature
    arm_payload = {
        "name": "Hero_Rig",
        "bones": {
            "Hips": {"name": "Hips", "parent_name": None, "children_names": ["Spine"]},
            "Spine": {"name": "Spine", "parent_name": "Hips", "children_names": []},
        },
        "total_bones": 2,
    }
    res_arm = tools.inspect_armature(arm_payload)
    assert res_arm["total_bones"] == 2

    # 4. Test diagnose_rig
    diag_res = tools.diagnose_rig(mesh_payload, arm_payload)
    assert "issues" in diag_res
    assert len(diag_res["issues"]) > 0


def test_mcp_fastmcp_json_wrapper():
    # Kiểm tra các tool function được expose qua JSON string
    mesh_json = json.dumps({
        "name": "TestHunyuan",
        "vertex_count": 48000,
        "polygon_count": 48000,
    })
    raw_str = inspect_mesh(mesh_json)
    parsed = json.loads(raw_str)
    assert parsed["name"] == "TestHunyuan"

    # Kiểm tra diagnose_rig qua JSON wrapper
    diag_str = diagnose_rig(mesh_data_json=mesh_json)
    diag_parsed = json.loads(diag_str)
    assert diag_parsed["mesh_name"] == "TestHunyuan"
