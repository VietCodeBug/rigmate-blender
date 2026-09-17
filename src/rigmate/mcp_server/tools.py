"""Định nghĩa các công cụ MCP chuẩn mực cho chẩn đoán và thao tác rig."""

from typing import Any, Dict, Optional
from rigmate.core.models import (
    SceneInfo,
    MeshInfo,
    ArmatureInfo,
    RigDiagnosticReport,
)
from rigmate.core.analyzer import RigAnalyzer


class RigMateMCPTools:
    """
    Tập hợp các công cụ MCP để AI Agent kiểm tra Blender.
    Hoạt động với dữ liệu thực từ Blender hoặc mock data.
    """

    def __init__(self, bpy_bridge_callback=None):
        """
        bpy_bridge_callback: Hàm callable gửi request tới Main Thread của Blender.
        Nếu None, có thể dùng mock data phục vụ kiểm thử.
        """
        self.bridge_cb = bpy_bridge_callback

    def inspect_scene(self, scene_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Công cụ 1: Đọc thông tin tổng quan scene Blender."""
        if scene_data:
            model = SceneInfo(**scene_data)
            return model.model_dump()
        return {
            "active_object_name": None,
            "selected_object_names": [],
            "objects": [],
            "unit_system": "METRIC",
            "note": "Không có scene_data được cung cấp.",
        }

    def inspect_mesh(self, mesh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Công cụ 2: Đọc thông tin chi tiết mesh của object được chỉ định."""
        mesh = MeshInfo(**mesh_data)
        return mesh.model_dump()

    def inspect_armature(self, armature_data: Dict[str, Any]) -> Dict[str, Any]:
        """Công cụ 3: Đọc armature, danh sách xương, quan hệ cha-con và liên kết."""
        armature = ArmatureInfo(**armature_data)
        return armature.model_dump()

    def diagnose_rig(
        self,
        mesh_data: Optional[Dict[str, Any]] = None,
        armature_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Công cụ 4: Báo cáo sơ bộ tình trạng rig dựa trên dữ liệu quan sát được.
        Đặc thù mô hình Hunyuan 3D + Meshy và xuất Godot.
        """
        mesh = MeshInfo(**mesh_data) if mesh_data else None
        armature = ArmatureInfo(**armature_data) if armature_data else None

        report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
        return report.model_dump()
