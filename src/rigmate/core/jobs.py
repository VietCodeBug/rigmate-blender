"""Job record domain model and strict lifecycle state machine.

Defines:
- JobStatus enum with canonical states
- Canonical state transition table
- Terminal state rules
- Durable JobRecord model aligning with Blueprint specification
"""

from enum import Enum
from typing import Dict, List, Literal, Optional, Set
from pydantic import BaseModel, Field, model_validator
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.receipts import ReceiptError
from rigmate.core.time_utils import to_utc_iso, parse_utc_iso


class JobStatus(str, Enum):
    QUEUED = "queued"
    INSPECTING = "inspecting"
    NEEDS_INPUT = "needs_input"
    PREPARED = "prepared"
    APPLYING = "applying"
    CANCEL_REQUESTED = "cancel_requested"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERY_REQUIRED = "recovery_required"
    RECOVERED = "recovered"


class JobType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    MUTATION = "mutation"
    RECOVERY = "recovery"


# Explicit canonical transition graph
ALLOWED_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.QUEUED: {
        JobStatus.INSPECTING,
        JobStatus.CANCELLED,
        JobStatus.FAILED,
    },
    JobStatus.INSPECTING: {
        JobStatus.NEEDS_INPUT,
        JobStatus.PREPARED,
        JobStatus.CANCELLED,
        JobStatus.FAILED,
    },
    JobStatus.NEEDS_INPUT: {
        JobStatus.INSPECTING,
        JobStatus.PREPARED,
        JobStatus.CANCELLED,
        JobStatus.FAILED,
    },
    JobStatus.PREPARED: {
        JobStatus.APPLYING,
        JobStatus.CANCELLED,
        JobStatus.FAILED,
    },
    JobStatus.APPLYING: {
        JobStatus.VERIFYING,
        JobStatus.CANCEL_REQUESTED,
        JobStatus.RECOVERY_REQUIRED,
        JobStatus.FAILED,
    },
    JobStatus.CANCEL_REQUESTED: {
        JobStatus.VERIFYING,
        JobStatus.RECOVERY_REQUIRED,
        JobStatus.FAILED,
    },
    JobStatus.VERIFYING: {
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.RECOVERY_REQUIRED,
    },
    JobStatus.RECOVERY_REQUIRED: {
        JobStatus.RECOVERED,
        JobStatus.FAILED,
    },
    # Terminal states: no transitions permitted
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
    JobStatus.RECOVERED: set(),
}

TERMINAL_STATUSES: Set[JobStatus] = {
    JobStatus.COMPLETED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
    JobStatus.RECOVERED,
}


def is_terminal_status(status: JobStatus) -> bool:
    """Check whether a given status is terminal."""
    return status in TERMINAL_STATUSES


def validate_transition(current_status: JobStatus, target_status: JobStatus) -> None:
    """
    Validate that transition from current_status to target_status is allowed.
    Raises RigMateError(INVALID_JOB_TRANSITION) if illegal or if current status is terminal.
    """
    if is_terminal_status(current_status):
        raise RigMateError(
            f"Cannot transition from terminal status '{current_status.value}' to '{target_status.value}'",
            code=RigMateErrorCode.INVALID_JOB_TRANSITION,
            details={
                "current_status": current_status.value,
                "target_status": target_status.value,
                "terminal": True,
            },
        )

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        allowed_names = sorted([s.value for s in allowed])
        raise RigMateError(
            f"Invalid job transition from '{current_status.value}' to '{target_status.value}'. "
            f"Allowed targets: {allowed_names}",
            code=RigMateErrorCode.INVALID_JOB_TRANSITION,
            details={
                "current_status": current_status.value,
                "target_status": target_status.value,
                "allowed_targets": allowed_names,
            },
        )


class JobRecord(BaseModel):
    """
    Durable materialized representation of a RigMate Job.
    Persisted to .rigmate/jobs/<job_id>/job.json.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    job_id: str
    project_id: str
    job_type: JobType = JobType.MUTATION

    status: JobStatus = JobStatus.QUEUED

    created_at: str = Field(default_factory=to_utc_iso)
    updated_at: str = Field(default_factory=to_utc_iso)

    correlation_id: str

    requested_by: str = "user"
    host_instance_id: str
    document_id: str

    expected_revision: str

    plan_ref: Optional[str] = None
    checkpoint_ref: Optional[str] = None

    current_operation_id: Optional[str] = None

    cancel_requested: bool = False
    last_event_sequence: int = -1

    terminal_reason: Optional[str] = None
    error: Optional[ReceiptError] = None

    @model_validator(mode="after")
    def validate_job_fields(self) -> "JobRecord":
        # Required non-empty strings
        for field_name in [
            "job_id",
            "project_id",
            "correlation_id",
            "requested_by",
            "host_instance_id",
            "document_id",
            "expected_revision",
        ]:
            val = getattr(self, field_name, None)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"JobRecord field '{field_name}' must be a non-empty string")

        # Validate timestamps
        parse_utc_iso(self.created_at)
        parse_utc_iso(self.updated_at)

        # Sequence check
        if self.last_event_sequence < -1:
            raise ValueError("last_event_sequence cannot be less than -1")

        # Completed/Recovered require no unresolved error
        if self.status in {JobStatus.COMPLETED, JobStatus.RECOVERED} and self.error is not None:
            raise ValueError(f"Job with status '{self.status.value}' cannot have an unresolved error")

        # Failed requires an error
        if self.status == JobStatus.FAILED and self.error is None:
            raise ValueError("Job with status 'failed' requires a structured error")

        return self
