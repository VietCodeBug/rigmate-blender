"""Model Context Protocol (MCP) tool implementations for Blender diagnostic analysis."""

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
    Standard MCP tools exposed to AI Agents for inspecting and diagnosing Blender.
    Operates on live Blender scene data or decoupled mock schemas.
    """

    def __init__(self, bpy_bridge_callback=None):
        self.bridge_cb = bpy_bridge_callback

    def inspect_scene(self, scene_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Tool 1: Read high-level scene overview and object summaries."""
        if scene_data:
            model = SceneInfo(**scene_data)
            return model.model_dump()
        return {
            "active_object_name": None,
            "selected_object_names": [],
            "objects": [],
            "unit_system": "METRIC",
            "note": "No scene_data provided.",
        }

    def inspect_mesh(self, mesh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tool 2: Read detailed mesh metrics (vertex count, modifiers, transforms)."""
        mesh = MeshInfo(**mesh_data)
        return mesh.model_dump()

    def inspect_armature(self, armature_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tool 3: Read armature bone list, hierarchy and deformation flags."""
        armature = ArmatureInfo(**armature_data)
        return armature.model_dump()

    def diagnose_rig(
        self,
        mesh_data: Optional[Dict[str, Any]] = None,
        armature_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Tool 4: Diagnostic report on rig and mesh readiness for Godot."""
        mesh = MeshInfo(**mesh_data) if mesh_data else None
        armature = ArmatureInfo(**armature_data) if armature_data else None

        report = RigAnalyzer.analyze(mesh=mesh, armature=armature)
        return report.model_dump()
