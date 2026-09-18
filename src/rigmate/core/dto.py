"""Pure standard-library data transfer objects (DTOs) for RigMate inspection.

Canonical DTOs live in `rigmate.contracts.dto` (pure Python standard library).
Re-exported here for Core convenience without any dependency on blender_addon.
"""

from rigmate.contracts.dto import (
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
