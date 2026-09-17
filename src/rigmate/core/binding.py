"""Canonical multi-entity identity binding validation for RigMate jobs.

Guarantees that:
- PreparedPlan matches JobRecord identity
- OperationEnvelope matches JobRecord identity and acquired lock scope
- CheckpointManifest matches JobRecord identity and OperationEnvelope
- OperationReceipt matches OperationEnvelope
Prevents cross-document mutation, cross-job artifact storage, and identity confusion.
"""

from typing import Optional
from rigmate.core.checkpoints import CheckpointManifest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.jobs import JobRecord
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.core.plans import PreparedPlan
from rigmate.core.receipts import OperationReceipt


def validate_job_binding(
    job: JobRecord,
    plan: Optional[PreparedPlan] = None,
    operation: Optional[OperationEnvelope] = None,
    checkpoint: Optional[CheckpointManifest] = None,
    receipt: Optional[OperationReceipt] = None,
) -> None:
    """
    Validate that all associated entities strictly belong to the specified JobRecord.
    Raises RigMateError with appropriate machine-readable code upon any mismatch.
    """
    # 1. Validate Plan binding
    if plan is not None:
        mismatches = []
        if plan.job_id != job.job_id:
            mismatches.append(f"job_id ('{plan.job_id}' != '{job.job_id}')")
        if plan.project_id != job.project_id:
            mismatches.append(f"project_id ('{plan.project_id}' != '{job.project_id}')")
        if plan.host_instance_id != job.host_instance_id:
            mismatches.append(f"host_instance_id ('{plan.host_instance_id}' != '{job.host_instance_id}')")
        if plan.document_id != job.document_id:
            mismatches.append(f"document_id ('{plan.document_id}' != '{job.document_id}')")
        if plan.expected_revision != job.expected_revision:
            mismatches.append(f"expected_revision ('{plan.expected_revision}' != '{job.expected_revision}')")

        if mismatches:
            raise RigMateError(
                f"Plan '{plan.plan_id}' does not match job '{job.job_id}': {', '.join(mismatches)}",
                code=RigMateErrorCode.JOB_BINDING_MISMATCH,
                details={
                    "job_id": job.job_id,
                    "plan_id": plan.plan_id,
                    "mismatches": mismatches,
                },
            )

    # 2. Validate Operation binding
    if operation is not None:
        mismatches = []
        if operation.job_id != job.job_id:
            mismatches.append(f"job_id ('{operation.job_id}' != '{job.job_id}')")
        if operation.project_id != job.project_id:
            mismatches.append(f"project_id ('{operation.project_id}' != '{job.project_id}')")
        if operation.host_instance_id != job.host_instance_id:
            mismatches.append(f"host_instance_id ('{operation.host_instance_id}' != '{job.host_instance_id}')")
        if operation.document_id != job.document_id:
            mismatches.append(f"document_id ('{operation.document_id}' != '{job.document_id}')")
        if operation.expected_revision != job.expected_revision:
            mismatches.append(f"expected_revision ('{operation.expected_revision}' != '{job.expected_revision}')")

        if operation.mode == OperationMode.APPLY:
            if operation.prepared_plan_ref != job.plan_ref:
                mismatches.append(f"prepared_plan_ref ('{operation.prepared_plan_ref}' != '{job.plan_ref}')")
            if operation.tool != "checkpoint.create":
                if operation.checkpoint_ref != job.checkpoint_ref:
                    mismatches.append(f"checkpoint_ref ('{operation.checkpoint_ref}' != '{job.checkpoint_ref}')")

        if mismatches:
            raise RigMateError(
                f"Operation '{operation.operation_id}' does not match job '{job.job_id}': {', '.join(mismatches)}",
                code=RigMateErrorCode.JOB_BINDING_MISMATCH,
                details={
                    "job_id": job.job_id,
                    "operation_id": operation.operation_id,
                    "mismatches": mismatches,
                },
            )

    # 3. Validate Checkpoint binding
    if checkpoint is not None:
        mismatches = []
        if checkpoint.job_id != job.job_id:
            mismatches.append(f"job_id ('{checkpoint.job_id}' != '{job.job_id}')")
        if checkpoint.project_id != job.project_id:
            mismatches.append(f"project_id ('{checkpoint.project_id}' != '{job.project_id}')")
        if checkpoint.checkpoint_id != job.checkpoint_ref:
            mismatches.append(f"checkpoint_id ('{checkpoint.checkpoint_id}' != '{job.checkpoint_ref}')")
        if checkpoint.source_revision != job.expected_revision:
            mismatches.append(f"source_revision ('{checkpoint.source_revision}' != '{job.expected_revision}')")

        if mismatches:
            raise RigMateError(
                f"Checkpoint manifest '{checkpoint.checkpoint_id}' does not match job '{job.job_id}': {', '.join(mismatches)}",
                code=RigMateErrorCode.CHECKPOINT_BINDING_MISMATCH,
                details={
                    "job_id": job.job_id,
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "mismatches": mismatches,
                },
            )

        if not checkpoint.complete or not checkpoint.verified_at:
            raise RigMateError(
                f"Checkpoint '{checkpoint.checkpoint_id}' is not complete or verified",
                code=RigMateErrorCode.CHECKPOINT_INCOMPLETE,
                details={"checkpoint_id": checkpoint.checkpoint_id},
            )

        if len(checkpoint.files) == 0:
            raise RigMateError(
                f"Checkpoint manifest '{checkpoint.checkpoint_id}' contains zero protected files",
                code=RigMateErrorCode.CHECKPOINT_INCOMPLETE,
                details={"checkpoint_id": checkpoint.checkpoint_id, "file_count": 0},
            )

        if operation is not None and operation.mode == OperationMode.APPLY and operation.tool != "checkpoint.create":
            if operation.checkpoint_ref != checkpoint.checkpoint_id:
                raise RigMateError(
                    f"Operation checkpoint_ref '{operation.checkpoint_ref}' does not match manifest '{checkpoint.checkpoint_id}'",
                    code=RigMateErrorCode.CHECKPOINT_BINDING_MISMATCH,
                    details={
                        "operation_checkpoint_ref": operation.checkpoint_ref,
                        "manifest_checkpoint_id": checkpoint.checkpoint_id,
                    },
                )

    # 4. Validate Receipt binding
    if receipt is not None:
        if operation is not None and receipt.operation_id != operation.operation_id:
            raise RigMateError(
                f"Receipt operation_id '{receipt.operation_id}' does not match operation '{operation.operation_id}'",
                code=RigMateErrorCode.RECEIPT_BINDING_MISMATCH,
                details={
                    "receipt_operation_id": receipt.operation_id,
                    "expected_operation_id": operation.operation_id,
                },
            )
        if receipt.host_revision_before is not None and receipt.host_revision_before != job.expected_revision:
            raise RigMateError(
                f"Receipt host_revision_before ({receipt.host_revision_before}) does not match job expected_revision ({job.expected_revision})",
                code=RigMateErrorCode.RECEIPT_BINDING_MISMATCH,
                details={
                    "receipt_revision": receipt.host_revision_before,
                    "expected_revision": job.expected_revision,
                },
            )

