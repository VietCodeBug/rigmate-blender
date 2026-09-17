"""Operation envelope domain model aligning with V1 Blueprint specification.

Enforces execution boundaries:
- Modes: inspect | preview | apply
- target_ids duplicate rejection
- In 'apply' mode: requires prepared_plan_ref and checkpoint_ref
  (with the sole exception of 'checkpoint.create')
- Strictly domain model: does NOT execute tools or access Blender/Godot
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class OperationMode(str, Enum):
    INSPECT = "inspect"
    PREVIEW = "preview"
    APPLY = "apply"


class OperationEnvelope(BaseModel):
    """
    Blueprint operation envelope representing an intended tool invocation.
    """
    schema_version: str = "1.0.0"
    operation_id: str
    job_id: str
    project_id: str
    host_instance_id: str
    document_id: str
    tool: str
    mode: OperationMode
    target_ids: List[str] = Field(default_factory=list)
    expected_revision: Optional[str] = None
    idempotency_key: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_ref: Optional[str] = None
    prepared_plan_ref: Optional[str] = None

    @model_validator(mode="after")
    def validate_envelope_rules(self) -> "OperationEnvelope":
        # 1. Non-empty string checks on required IDs
        for field_name in ["operation_id", "job_id", "project_id", "host_instance_id", "document_id", "tool", "idempotency_key"]:
            val = getattr(self, field_name, None)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"Field '{field_name}' must be a non-empty string")

        # 2. target_ids must not contain duplicates
        if len(self.target_ids) != len(set(self.target_ids)):
            raise ValueError("target_ids must not contain duplicate identifiers")

        # 3. Apply mode constraints
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
