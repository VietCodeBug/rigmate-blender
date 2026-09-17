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
    kind: str  # e.g. "revision_match", "file_exists", "vertex_count_below"
    expected_value: Any
    description: str = ""


class PlanPostcondition(BaseModel):
    """Postcondition predicate verified after operation execution."""
    kind: str  # e.g. "revision_changed", "file_hash_match", "field_equals"
    expected_value: Any
    description: str = ""


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
