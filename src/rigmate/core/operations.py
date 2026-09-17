"""Operation envelope domain model aligning with V1 Blueprint specification.

Enforces execution boundaries:
- schema_version strictly Literal["1.0.0"]
- Modes: inspect | preview | apply
- target_ids duplicate rejection & minimum 1 item required
- expected_revision required and non-empty string
- Required non-empty IDs: operation_id, job_id, project_id, host_instance_id, document_id, tool, expected_revision, idempotency_key
- In 'apply' mode: requires prepared_plan_ref and checkpoint_ref
  (with the sole exception of 'checkpoint.create')
- arguments validated for strict JSON compatibility (rejects bytes, Path, NaN, inf, raw objects)
- Strictly domain model: does NOT execute tools or access Blender/Godot
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from rigmate.core.json_types import assert_json_compatible, JsonCompatibilityError


class OperationMode(str, Enum):
    INSPECT = "inspect"
    PREVIEW = "preview"
    APPLY = "apply"


class OperationEnvelope(BaseModel):
    """
    Blueprint operation envelope representing an intended tool invocation.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    operation_id: str
    job_id: str
    project_id: str
    host_instance_id: str
    document_id: str
    tool: str
    mode: OperationMode
    target_ids: List[str]
    expected_revision: str
    idempotency_key: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_ref: Optional[str] = None
    prepared_plan_ref: Optional[str] = None

    @model_validator(mode="after")
    def validate_envelope_rules(self) -> "OperationEnvelope":
        # 1. Non-empty string checks on required IDs
        required_id_fields = [
            "operation_id",
            "job_id",
            "project_id",
            "host_instance_id",
            "document_id",
            "tool",
            "expected_revision",
            "idempotency_key",
        ]
        for field_name in required_id_fields:
            val = getattr(self, field_name, None)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"Field '{field_name}' must be a non-empty string")

        # 2. target_ids must contain at least one target and no duplicates
        if not self.target_ids:
            raise ValueError("target_ids must contain at least one target identifier")

        for idx, tid in enumerate(self.target_ids):
            if not isinstance(tid, str) or not tid.strip():
                raise ValueError(f"target_ids[{idx}] must be a non-empty string")

        if len(self.target_ids) != len(set(self.target_ids)):
            raise ValueError("target_ids must not contain duplicate identifiers")

        # 3. Arguments must be strictly JSON-compatible
        try:
            assert_json_compatible(self.arguments, path="$.arguments")
        except JsonCompatibilityError as e:
            raise ValueError(f"arguments validation failed: {e}") from e

        # 4. Apply mode constraints
        if self.mode == OperationMode.APPLY:
            # Must require prepared_plan_ref
            if not self.prepared_plan_ref or not self.prepared_plan_ref.strip():
                raise ValueError("Operations in 'apply' mode require a valid prepared_plan_ref")

            # Must require checkpoint_ref unless creating a checkpoint
            if self.tool != "checkpoint.create":
                if not self.checkpoint_ref or not self.checkpoint_ref.strip():
                    raise ValueError(
                        f"Operation '{self.tool}' in 'apply' mode requires a valid checkpoint_ref"
                    )

        return self
