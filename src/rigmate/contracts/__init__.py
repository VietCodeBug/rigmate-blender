"""RigMate neutral contracts package.

Pure Python standard library data contracts, DTOs, and transport protocols.
Zero external dependencies: NO Pydantic, NO FastAPI, NO MCP, NO bpy.
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
from rigmate.contracts.hashing import compute_operation_request_hash
from rigmate.contracts.host import (
    HostType,
    HostStatusEnum,
    HostIdentity,
    DocumentIdentity,
    InspectionRequest,
    InspectionResult,
    PreparedHostOperation,
    HostOperationRequest,
    HostApplyResult,
    HostOperationStatus,
    HostVerificationResult,
    HostAdapter,
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
    "compute_operation_request_hash",
    "HostType",
    "HostStatusEnum",
    "HostIdentity",
    "DocumentIdentity",
    "InspectionRequest",
    "InspectionResult",
    "PreparedHostOperation",
    "HostOperationRequest",
    "HostApplyResult",
    "HostOperationStatus",
    "HostVerificationResult",
    "HostAdapter",
]
