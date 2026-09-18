"""Neutral standard-library Data Transfer Objects (DTOs) for RigMate.

Completely decoupled from Pydantic, FastAPI, MCP, and Blender.
Uses strictly Python standard library dataclasses and typing.
Safe to import anywhere (Core, Blender add-on, Godot client, test runners).
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransformData":
        return cls(
            location=list(data.get("location", [0.0, 0.0, 0.0])),
            rotation_euler=list(data.get("rotation_euler", [0.0, 0.0, 0.0])),
            scale=list(data.get("scale", [1.0, 1.0, 1.0])),
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoneInfo":
        return cls(
            name=data["name"],
            parent_name=data.get("parent_name"),
            children_names=list(data.get("children_names", [])),
            head=list(data.get("head", [0.0, 0.0, 0.0])),
            tail=list(data.get("tail", [0.0, 0.0, 0.0])),
            length=float(data.get("length", 0.0)),
            connected=bool(data.get("connected", False)),
            use_deform=bool(data.get("use_deform", True)),
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArmatureInfo":
        raw_bones = data.get("bones", {})
        bones = {k: BoneInfo.from_dict(v) if isinstance(v, dict) else v for k, v in raw_bones.items()}
        trans = data.get("transform")
        trans_obj = TransformData.from_dict(trans) if isinstance(trans, dict) else (trans or TransformData())
        return cls(
            name=data["name"],
            bones=bones,
            root_bone_names=list(data.get("root_bone_names", [])),
            transform=trans_obj,
            total_bones=int(data.get("total_bones", len(bones))),
            deform_bones_count=int(data.get("deform_bones_count", len(bones))),
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VertexWeightSummary":
        return cls(
            unweighted_vertex_count=int(data.get("unweighted_vertex_count", 0)),
            max_weights_per_vertex=int(data.get("max_weights_per_vertex", 0)),
            exceeds_godot_max_weights=bool(data.get("exceeds_godot_max_weights", False)),
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeshInfo":
        trans = data.get("transform")
        trans_obj = TransformData.from_dict(trans) if isinstance(trans, dict) else (trans or TransformData())
        ws = data.get("weights_summary")
        ws_obj = VertexWeightSummary.from_dict(ws) if isinstance(ws, dict) else ws
        return cls(
            name=data["name"],
            vertex_count=int(data.get("vertex_count", 0)),
            edge_count=int(data.get("edge_count", 0)),
            polygon_count=int(data.get("polygon_count", 0)),
            has_armature_modifier=bool(data.get("has_armature_modifier", False)),
            target_armature_name=data.get("target_armature_name"),
            transform=trans_obj,
            vertex_groups=list(data.get("vertex_groups", [])),
            weights_summary=ws_obj,
            materials_count=int(data.get("materials_count", 0)),
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneObjectSummary":
        return cls(
            name=data["name"],
            type=data["type"],
            is_selected=bool(data.get("is_selected", False)),
            is_active=bool(data.get("is_active", False)),
            parent_name=data.get("parent_name"),
        )


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneInfo":
        objs = [
            SceneObjectSummary.from_dict(o) if isinstance(o, dict) else o
            for o in data.get("objects", [])
        ]
        return cls(
            active_object_name=data.get("active_object_name"),
            selected_object_names=list(data.get("selected_object_names", [])),
            objects=objs,
            unit_system=str(data.get("unit_system", "METRIC")),
        )


@dataclass
class DiagnosticIssue:
    """A single diagnostic issue or observation."""
    code: str
    severity: str  # INFO, SUGGESTION, WARNING, ERROR
    title: str
    message: str
    target_object: Optional[str] = None
    target_bone: Optional[str] = None
    suggested_action: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiagnosticIssue":
        return cls(
            code=data["code"],
            severity=data["severity"],
            title=data["title"],
            message=data["message"],
            target_object=data.get("target_object"),
            target_bone=data.get("target_bone"),
            suggested_action=data.get("suggested_action"),
        )


@dataclass
class FingerHeuristicSummary:
    """Heuristic detection summary for hand fingers."""
    hand_side: str  # LEFT or RIGHT
    detected_fingers: Dict[str, List[str]] = field(default_factory=dict)
    unmatched_patterns: List[str] = field(default_factory=list)
    total_finger_bones: int = 0
    recommendation: str = ""

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FingerHeuristicSummary":
        return cls(
            hand_side=data["hand_side"],
            detected_fingers=dict(data.get("detected_fingers", {})),
            unmatched_patterns=list(data.get("unmatched_patterns", [])),
            total_finger_bones=int(data.get("total_finger_bones", 0)),
            recommendation=str(data.get("recommendation", "")),
        )


@dataclass
class RigDiagnosticReport:
    """Overall diagnostic report for character rig and mesh."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mesh_name: Optional[str] = None
    armature_name: Optional[str] = None
    issues: List[DiagnosticIssue] = field(default_factory=list)
    finger_heuristics: List[FingerHeuristicSummary] = field(default_factory=list)
    godot_compatibility_score: str = ""
    ready_for_godot: bool = False
    summary_text: str = ""

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RigDiagnosticReport":
        issues = [
            DiagnosticIssue.from_dict(i) if isinstance(i, dict) else i
            for i in data.get("issues", [])
        ]
        heuristics = [
            FingerHeuristicSummary.from_dict(h) if isinstance(h, dict) else h
            for h in data.get("finger_heuristics", [])
        ]
        return cls(
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            mesh_name=data.get("mesh_name"),
            armature_name=data.get("armature_name"),
            issues=issues,
            finger_heuristics=heuristics,
            godot_compatibility_score=str(data.get("godot_compatibility_score", "")),
            ready_for_godot=bool(data.get("ready_for_godot", False)),
            summary_text=str(data.get("summary_text", "")),
        )
