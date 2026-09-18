"""Compatibility shim for Blender add-on DTOs.

Canonical implementations now live in `rigmate.contracts.dto` (pure Python standard library).
Re-exported here for backwards compatibility within the Blender add-on package.
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
