"""Prepared plan domain model for RigMate V1.

Represents a deterministic execution plan containing preconditions,
sequence of operations, expected scope, postconditions, and checkpoint requirement.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from rigmate.core.operations import OperationEnvelope
from rigmate.core.time_utils import to_utc_iso, parse_utc_iso


class PlanPrecondition(BaseModel):
    """Precondition assertion before operation execution."""
    kind: str  # e.g. "revision_match", "file_exists", "file_hash_match", "field_equals"
    expected_value: Any
    description: str = ""


class PlanPostcondition(BaseModel):
    """Postcondition predicate verified after operation execution."""
    kind: str  # e.g. "revision_changed", "file_hash_match", "field_equals"
    expected_value: Any
    description: str = ""


SUPPORTED_PREDICATE_KINDS = {
    "revision_match",
    "file_exists",
    "file_hash_match",
    "field_equals",
    "revision_changed",
}


def evaluate_predicate(kind: str, expected_value: Any, context: Dict[str, Any], description: str = "") -> None:
    """
    Deterministically evaluate a single predicate against context.
    Raises RigMateError(VALIDATION_FAILED) if predicate fails or kind is unsupported.
    """
    from pathlib import Path
    import hashlib
    from rigmate.core.errors import RigMateError, RigMateErrorCode

    if kind not in SUPPORTED_PREDICATE_KINDS:
        raise RigMateError(
            f"Unsupported predicate kind '{kind}' ({description or 'no description'})",
            code=RigMateErrorCode.VALIDATION_FAILED,
            details={"kind": kind, "supported": sorted(list(SUPPORTED_PREDICATE_KINDS))},
        )

    root = Path(context.get("project_root", "."))

    if kind == "revision_match":
        actual = context.get("current_revision") or context.get("revision") or context.get("expected_revision")
        if str(actual) != str(expected_value):
            raise RigMateError(
                f"Precondition failed: revision mismatch (expected '{expected_value}', got '{actual}')",
                code=RigMateErrorCode.VALIDATION_FAILED,
                details={"kind": kind, "expected": expected_value, "actual": actual},
            )

    elif kind == "file_exists":
        file_path = root / str(expected_value)
        if not file_path.is_file():
            raise RigMateError(
                f"Precondition failed: required file does not exist '{expected_value}'",
                code=RigMateErrorCode.VALIDATION_FAILED,
                details={"kind": kind, "path": str(expected_value)},
            )

    elif kind == "file_hash_match":
        # expected_value can be dict {"path": ..., "sha256": ...}
        if isinstance(expected_value, dict):
            rel_path = expected_value.get("path", "")
            exp_hash = expected_value.get("sha256", "")
        else:
            rel_path = str(expected_value)
            exp_hash = context.get("expected_hash", "")

        target = root / rel_path
        if not target.is_file():
            raise RigMateError(
                f"Predicate failed: file not found for hash verification '{rel_path}'",
                code=RigMateErrorCode.VALIDATION_FAILED,
                details={"kind": kind, "path": rel_path},
            )
        h = hashlib.sha256(target.read_bytes()).hexdigest()
        if h != exp_hash:
            raise RigMateError(
                f"Predicate failed: file hash mismatch for '{rel_path}' (expected '{exp_hash}', got '{h}')",
                code=RigMateErrorCode.VALIDATION_FAILED,
                details={"kind": kind, "path": rel_path, "expected_hash": exp_hash, "actual_hash": h},
            )

    elif kind == "field_equals":
        if isinstance(expected_value, dict):
            field_name = expected_value.get("field", "")
            exp_val = expected_value.get("value")
        else:
            field_name = str(expected_value)
            exp_val = context.get("expected_field_value")

        actual_val = context.get(field_name)
        if actual_val != exp_val:
            raise RigMateError(
                f"Predicate failed: field '{field_name}' value mismatch (expected '{exp_val}', got '{actual_val}')",
                code=RigMateErrorCode.VALIDATION_FAILED,
                details={"kind": kind, "field": field_name, "expected": exp_val, "actual": actual_val},
            )

    elif kind == "revision_changed":
        rev_before = context.get("host_revision_before") or context.get("expected_revision")
        rev_after = context.get("host_revision_after") or context.get("current_revision")
        if rev_before == rev_after:
            raise RigMateError(
                f"Postcondition failed: revision did not advance (remained '{rev_before}')",
                code=RigMateErrorCode.VALIDATION_FAILED,
                details={"kind": kind, "revision_before": rev_before, "revision_after": rev_after},
            )


def evaluate_preconditions(preconditions: List[PlanPrecondition], context: Dict[str, Any]) -> None:
    """Evaluate all preconditions in order."""
    for p in preconditions:
        evaluate_predicate(p.kind, p.expected_value, context, p.description)


def evaluate_postconditions(postconditions: List[PlanPostcondition], context: Dict[str, Any]) -> None:
    """Evaluate all postconditions in order."""
    for p in postconditions:
        evaluate_predicate(p.kind, p.expected_value, context, p.description)



class PreparedPlan(BaseModel):
    """
    Durable execution plan. Persisted to .rigmate/jobs/<job_id>/plan.json.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    plan_id: str
    job_id: str
    project_id: str
    created_at: str = Field(default_factory=to_utc_iso)

    host_instance_id: str
    document_id: str
    expected_revision: str

    operations: List[OperationEnvelope] = Field(default_factory=list)

    preconditions: List[PlanPrecondition] = Field(default_factory=list)
    postconditions: List[PlanPostcondition] = Field(default_factory=list)

    scope: List[str] = Field(default_factory=list)  # Target object or bone names
    checkpoint_required: bool = True

    @model_validator(mode="after")
    def validate_plan_fields(self) -> "PreparedPlan":
        for field_name in [
            "plan_id",
            "job_id",
            "project_id",
            "host_instance_id",
            "document_id",
            "expected_revision",
        ]:
            val = getattr(self, field_name, None)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"PreparedPlan field '{field_name}' must be a non-empty string")

        parse_utc_iso(self.created_at)
        return self
