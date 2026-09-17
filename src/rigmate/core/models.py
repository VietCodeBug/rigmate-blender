"""Cấu trúc dữ liệu độc lập hoàn toàn với Blender (bpy)."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class TransformData(BaseModel):
    """Lưu trữ transform (vị trí, xoay, tỷ lệ) để kiểm tra unapplied transform."""
    location: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])

    def is_applied(self, tolerance: float = 1e-4) -> bool:
        """Kiểm tra scale có bằng 1.0 và rotation có bằng 0.0 không."""
        scale_ok = all(abs(s - 1.0) < tolerance for s in self.scale)
        rot_ok = all(abs(r) < tolerance for r in self.rotation_euler)
        return scale_ok and rot_ok


class BoneInfo(BaseModel):
    """Thông tin về một bone trong armature."""
    name: str
    parent_name: Optional[str] = None
    children_names: List[str] = Field(default_factory=list)
    head: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    tail: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    length: float = 0.0
    connected: bool = False
    use_deform: bool = True


class ArmatureInfo(BaseModel):
    """Thông tin armature và phân cấp xương."""
    name: str
    bones: Dict[str, BoneInfo] = Field(default_factory=dict)
    root_bone_names: List[str] = Field(default_factory=list)
    transform: TransformData = Field(default_factory=TransformData)
    total_bones: int = 0
    deform_bones_count: int = 0


class VertexWeightSummary(BaseModel):
    """Tóm tắt phân bổ trọng số vertex."""
    unweighted_vertex_count: int = 0
    max_weights_per_vertex: int = 0
    exceeds_godot_max_weights: bool = False  # Godot mặc định tối đa 4 (hoặc 8 nếu bật 8-weights)


class MeshInfo(BaseModel):
    """Thông tin chi tiết về mesh (đặc thù Hunyuan 3D khoảng ~50k đỉnh)."""
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
    """Tóm tắt nhanh một object trong scene Blender."""
    name: str
    type: str  # MESH, ARMATURE, CAMERA, LIGHT, EMPTY,...
    is_selected: bool = False
    is_active: bool = False
    parent_name: Optional[str] = None


class SceneInfo(BaseModel):
    """Toàn cảnh scene hiện tại."""
    active_object_name: Optional[str] = None
    selected_object_names: List[str] = Field(default_factory=list)
    objects: List[SceneObjectSummary] = Field(default_factory=list)
    unit_system: str = "METRIC"


class DiagnosticSeverity(BaseModel):
    """Phân loại mức độ cảnh báo."""
    INFO: str = "INFO"
    SUGGESTION: str = "SUGGESTION"
    WARNING: str = "WARNING"
    ERROR: str = "ERROR"


class DiagnosticIssue(BaseModel):
    """Một mục vấn đề hoặc phát hiện trong quá trình chẩn đoán."""
    code: str
    severity: str  # INFO, SUGGESTION, WARNING, ERROR
    title: str
    message: str
    target_object: Optional[str] = None
    target_bone: Optional[str] = None
    suggested_action: Optional[str] = None


class FingerHeuristicSummary(BaseModel):
    """Tóm tắt nhận diện ngón tay heuristic."""
    hand_side: str  # LEFT, RIGHT, UNKNOWN
    detected_fingers: Dict[str, List[str]] = Field(default_factory=dict)
    # Ví dụ: {"thumb": ["thumb_01", "thumb_02"], "index": [...]}
    confidence_note: str = "Tên xương chỉ là gợi ý heuristic, không khẳng định thiếu ngón nếu model dùng quy ước khác."


class RigDiagnosticReport(BaseModel):
    """Báo cáo sơ bộ toàn diện về tình trạng Rig và Mesh."""
    timestamp: str
    mesh_name: Optional[str] = None
    armature_name: Optional[str] = None
    issues: List[DiagnosticIssue] = Field(default_factory=list)
    finger_heuristics: List[FingerHeuristicSummary] = Field(default_factory=list)
    godot_compatibility_score: str = "Chưa đánh giá"  # TỐT, CẦN LƯU Ý, CẦN SỬA
    summary_text: str = ""
