"""Centralized structured error model for RigMate.

Provides machine-readable error codes aligned with V1 contracts,
JSON serialization, optional structured details, and exception causality.
"""

from typing import Any, Dict, Optional


class RigMateErrorCode:
    """Stable canonical machine-readable error codes."""
    HOST_UNAVAILABLE = "HOST_UNAVAILABLE"
    VERSION_UNSUPPORTED = "VERSION_UNSUPPORTED"
    TARGET_STALE = "TARGET_STALE"
    SCOPE_AMBIGUOUS = "SCOPE_AMBIGUOUS"
    TOPOLOGY_UNSUITABLE = "TOPOLOGY_UNSUITABLE"
    CHECKPOINT_FAILED = "CHECKPOINT_FAILED"
    DISK_BUDGET_EXCEEDED = "DISK_BUDGET_EXCEEDED"
    PROVIDER_AUTH_REQUIRED = "PROVIDER_AUTH_REQUIRED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    QUOTA_UNKNOWN = "QUOTA_UNKNOWN"
    CANCEL_PENDING = "CANCEL_PENDING"
    RESULT_UNVERIFIED = "RESULT_UNVERIFIED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    OUT_OF_SCOPE_PATH = "OUT_OF_SCOPE_PATH"
    READ_ONLY_SOURCE = "READ_ONLY_SOURCE"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Job lifecycle & execution codes
    INVALID_JOB_TRANSITION = "INVALID_JOB_TRANSITION"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_ALREADY_TERMINAL = "JOB_ALREADY_TERMINAL"
    CHECKPOINT_REQUIRED = "CHECKPOINT_REQUIRED"
    CHECKPOINT_INCOMPLETE = "CHECKPOINT_INCOMPLETE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    OPERATION_STATUS_UNKNOWN = "OPERATION_STATUS_UNKNOWN"
    LOCK_CONFLICT = "LOCK_CONFLICT"
    LOCK_STALE = "LOCK_STALE"
    EVENT_SEQUENCE_INVALID = "EVENT_SEQUENCE_INVALID"
    JOURNAL_INCONSISTENT = "JOURNAL_INCONSISTENT"
    JOB_BINDING_MISMATCH = "JOB_BINDING_MISMATCH"
    ARTIFACT_PATH_INVALID = "ARTIFACT_PATH_INVALID"
    CHECKPOINT_BINDING_MISMATCH = "CHECKPOINT_BINDING_MISMATCH"
    RECEIPT_BINDING_MISMATCH = "RECEIPT_BINDING_MISMATCH"
    RECOVERY_EVIDENCE_INCOMPLETE = "RECOVERY_EVIDENCE_INCOMPLETE"
    LOCK_CORRUPT = "LOCK_CORRUPT"


class RigMateError(Exception):
    """
    Base structured exception for RigMate.
    - code: Stable machine-readable string (used by UI for translation)
    - message: Internal canonical English description
    - details: Optional dictionary of structured context (scrubbed of secrets)
    """

    def __init__(
        self,
        message: str,
        code: str = RigMateErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
        if cause:
            self.__cause__ = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to JSON-serializable dictionary."""
        d: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
        if self.cause:
            d["cause"] = f"{type(self.cause).__name__}: {self.cause}"
        return d

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} (details={self.details})"
        return f"[{self.code}] {self.message}"
