"""Operation execution receipt domain model aligning with V1 Blueprint specification.

Enforces:
- schema_version strictly Literal["1.0.0"]
- operation_id required and non-empty
- host_revision_before required and non-empty (cannot be None)
- Completed & recovered status require verified_at and host_revision_after
- Completed & recovered status reject unresolved error objects
- Failed status requires a structured ReceiptError
- ReceiptError enforces code and message
- Facts and changes strictly validated for JSON compatibility
- Tool execution success is strictly distinct from verified completion
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from rigmate.core.time_utils import parse_utc_iso
from rigmate.core.json_types import assert_json_compatible, JsonCompatibilityError


class ReceiptStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERY_REQUIRED = "recovery_required"
    RECOVERED = "recovered"


class ReceiptError(BaseModel):
    """Structured error object within an operation receipt."""
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_error_fields(self) -> "ReceiptError":
        if not self.code or not self.code.strip():
            raise ValueError("ReceiptError 'code' must be a non-empty string")
        if not self.message or not self.message.strip():
            raise ValueError("ReceiptError 'message' must be a non-empty string")
        try:
            assert_json_compatible(self.details, path="$.error.details")
        except JsonCompatibilityError as e:
            raise ValueError(f"error.details validation failed: {e}") from e
        return self


class OperationReceipt(BaseModel):
    """
    Receipt recording the verified outcome of an OperationEnvelope.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    operation_id: str
    status: ReceiptStatus
    host_revision_before: str
    host_revision_after: Optional[str] = None
    facts: Dict[str, Any] = Field(default_factory=dict)
    changes: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    artifact_refs: List[str] = Field(default_factory=list)
    verified_at: Optional[str] = None
    error: Optional[ReceiptError] = None

    @model_validator(mode="after")
    def validate_receipt_contracts(self) -> "OperationReceipt":
        # 1. Non-empty string checks on required IDs
        if not self.operation_id or not self.operation_id.strip():
            raise ValueError("Field 'operation_id' must be a non-empty string")
        if not self.host_revision_before or not self.host_revision_before.strip():
            raise ValueError("Field 'host_revision_before' must be a non-empty string")

        # 2. Check verified_at format if provided
        if self.verified_at:
            if not self.verified_at.strip():
                raise ValueError("Field 'verified_at' cannot be an empty string if provided")
            parse_utc_iso(self.verified_at)

        # 3. Validate JSON compatibility of facts and changes
        try:
            assert_json_compatible(self.facts, path="$.facts")
            assert_json_compatible(self.changes, path="$.changes")
        except JsonCompatibilityError as e:
            raise ValueError(f"Receipt payload validation failed: {e}") from e

        # 4. 'completed' requires verified_at, host_revision_after, and no error
        if self.status == ReceiptStatus.COMPLETED:
            if not self.verified_at:
                raise ValueError("Status 'completed' requires a valid 'verified_at' timestamp")
            if not self.host_revision_after or not self.host_revision_after.strip():
                raise ValueError("Status 'completed' requires 'host_revision_after'")
            if self.error is not None:
                raise ValueError("Status 'completed' cannot have an unresolved 'error'")

        # 5. 'recovered' requires verified_at, host_revision_after, and no unresolved error
        elif self.status == ReceiptStatus.RECOVERED:
            if not self.verified_at:
                raise ValueError("Status 'recovered' requires a valid 'verified_at' timestamp")
            if not self.host_revision_after or not self.host_revision_after.strip():
                raise ValueError("Status 'recovered' requires 'host_revision_after'")
            if self.error is not None:
                raise ValueError("Status 'recovered' cannot have an unresolved 'error'")

        # 6. 'failed' requires a structured error object
        elif self.status == ReceiptStatus.FAILED:
            if self.error is None:
                raise ValueError("Status 'failed' requires a structured 'error' object")

        return self
