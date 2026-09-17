"""Pure standard-library data transfer objects (DTOs) for RigMate inspection.

Decoupled completely from Pydantic and external server dependencies.
Uses only Python standard library `dataclasses` and `typing`.
Re-exports canonical DTOs from blender_addon.dto.
"""

from rigmate.blender_addon.dto import (
    TransformData,
    BoneInfo,
    ArmatureInfo,
    VertexWeightSummary,
    MeshInfo,
    SceneObjectSummary,
    SceneInfo,
    DiagnosticIssue,
    FingerHeuristicSummary,
    RigDiagnosticReport,
)

__all__ = [
    "TransformData",
    "BoneInfo",
    "ArmatureInfo",
    "VertexWeightSummary",
    "MeshInfo",
    "SceneObjectSummary",
    "SceneInfo",
    "DiagnosticIssue",
    "FingerHeuristicSummary",
    "RigDiagnosticReport",
]
