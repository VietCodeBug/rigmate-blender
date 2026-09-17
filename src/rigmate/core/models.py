"""Data models and schemas decoupled completely from Blender (bpy)."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class TransformData(BaseModel):
    """Object transform (location, rotation, scale) to verify unapplied transforms."""
    location: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])

    def is_applied(self, tolerance: float = 1e-4) -> bool:
        """Check whether scale equals 1.0 and rotation equals 0.0 within tolerance."""
        scale_ok = all(abs(s - 1.0) < tolerance for s in self.scale)
        rot_ok = all(abs(r) < tolerance for r in self.rotation_euler)
        return scale_ok and rot_ok


class BoneInfo(BaseModel):
    """Information for a single armature bone."""
    name: str
    parent_name: Optional[str] = None
    children_names: List[str] = Field(default_factory=list)
    head: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    tail: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    length: float = 0.0
    connected: bool = False
    use_deform: bool = True


class ArmatureInfo(BaseModel):
    """Armature hierarchy and bone metadata."""
    name: str
    bones: Dict[str, BoneInfo] = Field(default_factory=dict)
    root_bone_names: List[str] = Field(default_factory=list)
    transform: TransformData = Field(default_factory=TransformData)
    total_bones: int = 0
    deform_bones_count: int = 0


class VertexWeightSummary(BaseModel):
    """Summary of vertex skinning influence weights."""
    unweighted_vertex_count: int = 0
    max_weights_per_vertex: int = 0
    exceeds_godot_max_weights: bool = False  # Godot supports 4 weights/vertex (or 8 with 8-weights enabled)


class MeshInfo(BaseModel):
    """Detailed mesh metrics (e.g. Hunyuan 3D ~50k vertices)."""
    name: str
    vertex_count: int = 0
    edge_count: int = 0
    polygon_count: int = 0
    has_armature_modifier: bool = False
    target_armature_name: Optional[str] = None
    transform: TransformData = Field(default_factory=TransformData)
    vertex_groups: List[str] = Field(default_factory=list)
    weights_summary: Optional[VertexWeightSummary] = None
    materials_count: int = 0


class SceneObjectSummary(BaseModel):
    """High-level summary of an object in Blender scene."""
    name: str
    type: str  # MESH, ARMATURE, CAMERA, LIGHT, EMPTY,...
    is_selected: bool = False
    is_active: bool = False
    parent_name: Optional[str] = None


class SceneInfo(BaseModel):
    """Full scene overview."""
    active_object_name: Optional[str] = None
    selected_object_names: List[str] = Field(default_factory=list)
    objects: List[SceneObjectSummary] = Field(default_factory=list)
    unit_system: str = "METRIC"


class DiagnosticSeverity(BaseModel):
    """Severity classification constants."""
    INFO: str = "INFO"
    SUGGESTION: str = "SUGGESTION"
    WARNING: str = "WARNING"
    ERROR: str = "ERROR"


class DiagnosticIssue(BaseModel):
    """A single diagnostic issue or observation."""
    code: str
    severity: str  # INFO, SUGGESTION, WARNING, ERROR
    title: str
    message: str
    target_object: Optional[str] = None
    target_bone: Optional[str] = None
    suggested_action: Optional[str] = None


class FingerHeuristicSummary(BaseModel):
    """Heuristic detection summary for hand fingers."""
    hand_side: str  # LEFT, RIGHT, UNKNOWN
    detected_fingers: Dict[str, List[str]] = Field(default_factory=dict)
    confidence_note: str = "Bone names are heuristic suggestions and do not strictly confirm missing fingers."


class RigDiagnosticReport(BaseModel):
    """Comprehensive diagnostic report on rig and mesh readiness."""
    timestamp: str
    mesh_name: Optional[str] = None
    armature_name: Optional[str] = None
    issues: List[DiagnosticIssue] = Field(default_factory=list)
    finger_heuristics: List[FingerHeuristicSummary] = Field(default_factory=list)
    godot_compatibility_score: str = "UNASSESSED"  # GOOD, NEEDS ATTENTION, NEEDS FIX
    summary_text: str = ""
