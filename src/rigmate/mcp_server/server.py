"""Server MCP công bố các công cụ RigMate cho AI Agent."""

import json
from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from rigmate.mcp_server.tools import RigMateMCPTools

mcp_app = FastMCP("rigmate-tools")
tools_impl = RigMateMCPTools()


@mcp_app.tool()
def inspect_scene(scene_data_json: Optional[str] = None) -> str:
    """Đọc thông tin scene hiện tại trong Blender."""
    data = json.loads(scene_data_json) if scene_data_json else None
    result = tools_impl.inspect_scene(data)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp_app.tool()
def inspect_mesh(mesh_data_json: str) -> str:
    """Đọc thông tin mesh (số đỉnh, modifier, transforms) của object."""
    data = json.loads(mesh_data_json)
    result = tools_impl.inspect_mesh(data)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp_app.tool()
def inspect_armature(armature_data_json: str) -> str:
    """Đọc bộ xương armature (danh sách xương, quan hệ cha-con)."""
    data = json.loads(armature_data_json)
    result = tools_impl.inspect_armature(data)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp_app.tool()
def diagnose_rig(mesh_data_json: Optional[str] = None, armature_data_json: Optional[str] = None) -> str:
    """Chẩn đoán sơ bộ tình trạng rig nhân vật Hunyuan 3D + Meshy hướng tới Godot."""
    mesh_data = json.loads(mesh_data_json) if mesh_data_json else None
    arm_data = json.loads(armature_data_json) if armature_data_json else None
    result = tools_impl.diagnose_rig(mesh_data, arm_data)
    return json.dumps(result, ensure_ascii=False, indent=2)


def run_mcp_server():
    """Khởi chạy MCP server qua STDIO."""
    mcp_app.run()


if __name__ == "__main__":
    run_mcp_server()
