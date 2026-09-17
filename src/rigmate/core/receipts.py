"""Operation execution receipt domain model aligning with V1 Blueprint specification.

Enforces:
- Completed & recovered status require verified_at and host_revision_after
- Completed & recovered status reject unresolved error objects
- Tool execution success is strictly distinct from verified completion
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from rigmate.core.time_utils import parse_utc_iso


class ReceiptStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERY_REQUIRED = "recovery_required"
    RECOVERED = "recovered"


class OperationReceipt(BaseModel):
    """
    Receipt recording the verified outcome of an OperationEnvelope.
    """
    schema_version: str = "1.0.0"
    operation_id: str
    status: ReceiptStatus
    host_revision_before: Optional[str] = None
    host_revision_after: Optional[str] = None
    facts: Dict[str, Any] = Field(default_factory=dict)
    changes: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    artifact_refs: List[str] = Field(default_factory=list)
    verified_at: Optional[str] = None
    error: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_receipt_contracts(self) -> "OperationReceipt":
        # Check verified_at format if provided
        if self.verified_at:
            parse_utc_iso(self.verified_at)

        # 1. 'completed' requires verified_at, host_revision_after, and no error
        if self.status == ReceiptStatus.COMPLETED:
            if not self.verified_at:
                raise ValueError("Status 'completed' requires a valid 'verified_at' timestamp")
            if not self.host_revision_after:
                raise ValueError("Status 'completed' requires 'host_revision_after'")
            if self.error is not None:
                raise ValueError("Status 'completed' cannot have an unresolved 'error'")

        # 2. 'recovered' requires verified_at, host_revision_after, and no unresolved error
        elif self.status == ReceiptStatus.RECOVERED:
            if not self.verified_at:
                raise ValueError("Status 'recovered' requires a valid 'verified_at' timestamp")
            if not self.host_revision_after:
                raise ValueError("Status 'recovered' requires 'host_revision_after'")
            if self.error is not None:
                raise ValueError("Status 'recovered' cannot have an unresolved 'error'")

        # 3. 'failed' should generally have an error description
        elif self.status == ReceiptStatus.FAILED:
            if self.error is None:
                raise ValueError("Status 'failed' requires an 'error' object")

        return self
