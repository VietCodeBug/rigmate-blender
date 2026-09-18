"""Core host protocol integration and adapter utilities for RigMate V1.

Re-exports transport-neutral contracts from `rigmate.contracts.host` and
provides Core-side domain conversions from `OperationEnvelope` -> `HostOperationRequest`.
"""

from typing import Union
from rigmate.contracts.host import (
    HostType,
    HostStatusEnum,
    HostOperationExecutionState,
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
from rigmate.core.operations import OperationEnvelope


def host_request_from_operation(op: Union[OperationEnvelope, HostOperationRequest]) -> HostOperationRequest:
    """Convert Core domain OperationEnvelope into transport-neutral HostOperationRequest."""
    if isinstance(op, HostOperationRequest):
        return op

    return HostOperationRequest(
        schema_version=getattr(op, "schema_version", "1.0.0"),
        operation_id=op.operation_id,
        job_id=op.job_id,
        project_id=op.project_id,
        host_instance_id=op.host_instance_id,
        document_id=op.document_id,
        tool=op.tool,
        mode=op.mode.value if hasattr(op.mode, "value") else str(op.mode),
        target_ids=list(op.target_ids),
        expected_revision=op.expected_revision,
        idempotency_key=op.idempotency_key,
        arguments=dict(op.arguments),
        prepared_plan_ref=op.prepared_plan_ref,
        checkpoint_ref=op.checkpoint_ref,
    )


__all__ = [
    "HostType",
    "HostStatusEnum",
    "HostOperationExecutionState",
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
    "host_request_from_operation",
]
