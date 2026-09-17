"""Pure standard-library data transfer objects (DTOs) for Blender add-on inspection.

Decoupled completely from Pydantic and external server dependencies.
Uses only Python standard library `dataclasses` and `typing`.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TransformData:
    """Object transform (location, rotation, scale) to verify unapplied transforms."""
    location: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])

    def is_applied(self, tolerance: float = 1e-4) -> bool:
        """Check whether scale equals 1.0 and rotation equals 0.0 within tolerance."""
        scale_ok = all(abs(s - 1.0) < tolerance for s in self.scale)
        rot_ok = all(abs(r) < tolerance for r in self.rotation_euler)
        return scale_ok and rot_ok

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BoneInfo:
    """Information for a single armature bone."""
    name: str
    parent_name: Optional[str] = None
    children_names: List[str] = field(default_factory=list)
    head: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    tail: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    length: float = 0.0
    connected: bool = False
    use_deform: bool = True

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArmatureInfo:
    """Armature hierarchy and bone metadata."""
    name: str
    bones: Dict[str, BoneInfo] = field(default_factory=dict)
    root_bone_names: List[str] = field(default_factory=list)
    transform: TransformData = field(default_factory=TransformData)
    total_bones: int = 0
    deform_bones_count: int = 0

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VertexWeightSummary:
    """Summary of vertex skinning influence weights."""
    unweighted_vertex_count: int = 0
    max_weights_per_vertex: int = 0
    exceeds_godot_max_weights: bool = False

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeshInfo:
    """Detailed mesh metrics (e.g. Hunyuan 3D ~50k vertices)."""
    name: str
    vertex_count: int = 0
    edge_count: int = 0
    polygon_count: int = 0
    has_armature_modifier: bool = False
    target_armature_name: Optional[str] = None
    transform: TransformData = field(default_factory=TransformData)
    vertex_groups: List[str] = field(default_factory=list)
    weights_summary: Optional[VertexWeightSummary] = None
    materials_count: int = 0

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SceneObjectSummary:
    """High-level summary of an object in Blender scene."""
    name: str
    type: str  # MESH, ARMATURE, CAMERA, LIGHT, EMPTY,...
    is_selected: bool = False
    is_active: bool = False
    parent_name: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SceneInfo:
    """Full scene overview."""
    active_object_name: Optional[str] = None
    selected_object_names: List[str] = field(default_factory=list)
    objects: List[SceneObjectSummary] = field(default_factory=list)
    unit_system: str = "METRIC"

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
