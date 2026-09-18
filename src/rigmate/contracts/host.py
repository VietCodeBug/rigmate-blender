"""Transport-neutral host control plane protocol for RigMate V1.

Pure Python standard library (dataclasses, enum, typing).
Zero external dependencies: NO Pydantic, NO FastAPI, NO MCP, NO bpy.
Safe for Blender embedded Python, external Core, and standalone tests.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HostType(str, Enum):
    FAKE = "fake"
    BLENDER = "blender"
    GODOT = "godot"


class HostStatusEnum(str, Enum):
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class HostOperationExecutionState(str, Enum):
    APPLIED = "applied"
    FAILED = "failed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


@dataclass
class HostIdentity:
    """Host environment identity."""
    host_instance_id: str
    host_type: str = HostType.FAKE.value
    protocol_version: str = "1.0.0"
    details: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostIdentity":
        return cls(
            host_instance_id=data["host_instance_id"],
            host_type=data.get("host_type", HostType.FAKE.value),
            protocol_version=data.get("protocol_version", "1.0.0"),
            details=dict(data.get("details", {})),
        )


@dataclass
class DocumentIdentity:
    """Document and revision identity in host runtime."""
    project_id: str
    document_id: str
    revision: str

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentIdentity":
        return cls(
            project_id=data["project_id"],
            document_id=data["document_id"],
            revision=data["revision"],
        )


@dataclass
class InspectionRequest:
    """Request to inspect document state without mutation."""
    project_id: str
    document_id: str
    scope: Optional[List[str]] = None
    include_geometry: bool = False
    include_weights: bool = False

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InspectionRequest":
        return cls(
            project_id=data["project_id"],
            document_id=data["document_id"],
            scope=list(data["scope"]) if data.get("scope") is not None else None,
            include_geometry=bool(data.get("include_geometry", False)),
            include_weights=bool(data.get("include_weights", False)),
        )


@dataclass
class InspectionResult:
    """Host inspection outcome."""
    document: DocumentIdentity
    facts: Dict[str, Any] = field(default_factory=dict)
    scene_objects: List[Dict[str, Any]] = field(default_factory=list)
    inspected_at: str = field(default_factory=_utc_now_iso)

    def model_dump(self) -> Dict[str, Any]:
        res = asdict(self)
        if isinstance(self.document, DocumentIdentity):
            res["document"] = self.document.to_dict()
        return res

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InspectionResult":
        doc_data = data["document"]
        doc = DocumentIdentity.from_dict(doc_data) if isinstance(doc_data, dict) else doc_data
        return cls(
            document=doc,
            facts=dict(data.get("facts", {})),
            scene_objects=list(data.get("scene_objects", [])),
            inspected_at=data.get("inspected_at", _utc_now_iso()),
        )


@dataclass
class PreparedHostOperation:
    """Result of host-level precondition validation (read-only)."""
    operation_id: str
    document: DocumentIdentity
    tool: str
    mode: str
    can_apply: bool
    rejection_reason: Optional[str] = None
    prepared_at: str = field(default_factory=_utc_now_iso)

    def model_dump(self) -> Dict[str, Any]:
        res = asdict(self)
        if isinstance(self.document, DocumentIdentity):
            res["document"] = self.document.to_dict()
        return res

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreparedHostOperation":
        doc_data = data["document"]
        doc = DocumentIdentity.from_dict(doc_data) if isinstance(doc_data, dict) else doc_data
        return cls(
            operation_id=data["operation_id"],
            document=doc,
            tool=data["tool"],
            mode=data["mode"],
            can_apply=bool(data["can_apply"]),
            rejection_reason=data.get("rejection_reason"),
            prepared_at=data.get("prepared_at", _utc_now_iso()),
        )


@dataclass
class HostOperationRequest:
    """
    Transport-neutral mutation operation envelope sent to host.
    Decoupled completely from Core Pydantic OperationEnvelope.
    """
    operation_id: str
    job_id: str
    project_id: str
    host_instance_id: str
    document_id: str
    tool: str
    mode: str = "apply"
    target_ids: List[str] = field(default_factory=list)
    expected_revision: Optional[str] = None
    idempotency_key: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    prepared_plan_ref: Optional[str] = None
    checkpoint_ref: Optional[str] = None
    schema_version: str = "1.0.0"

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostOperationRequest":
        return cls(
            operation_id=data["operation_id"],
            job_id=data["job_id"],
            project_id=data["project_id"],
            host_instance_id=data["host_instance_id"],
            document_id=data["document_id"],
            tool=data["tool"],
            mode=str(data.get("mode", "apply")),
            target_ids=list(data.get("target_ids", [])),
            expected_revision=data.get("expected_revision"),
            idempotency_key=str(data.get("idempotency_key", "")),
            arguments=dict(data.get("arguments", {})),
            prepared_plan_ref=data.get("prepared_plan_ref"),
            checkpoint_ref=data.get("checkpoint_ref"),
            schema_version=str(data.get("schema_version", "1.0.0")),
        )


@dataclass
class HostApplyResult:
    """
    Immediate result of host mutation execution.
    Distinct from verified completion receipt!
    """
    operation_id: str
    execution_state: str = HostOperationExecutionState.APPLIED.value
    host_revision_before: str = ""
    host_revision_after: str = ""
    facts: Dict[str, Any] = field(default_factory=dict)
    changes: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
    executed_at: str = field(default_factory=_utc_now_iso)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostApplyResult":
        return cls(
            operation_id=data["operation_id"],
            execution_state=data.get("execution_state", HostOperationExecutionState.APPLIED.value),
            host_revision_before=data.get("host_revision_before", ""),
            host_revision_after=data.get("host_revision_after", ""),
            facts=dict(data.get("facts", {})),
            changes=list(data.get("changes", [])),
            error=dict(data["error"]) if data.get("error") else None,
            executed_at=data.get("executed_at", _utc_now_iso()),
        )


@dataclass
class HostOperationStatus:
    """
    Authoritative durable host execution status retrieved via query_operation_status.
    Explicitly distinguishes EXECUTED, NOT_FOUND, UNKNOWN, and UNAVAILABLE.
    """
    state: HostStatusEnum
    operation_id: str
    idempotency_key: str
    apply_result: Optional[HostApplyResult] = None
    authoritative: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    queried_at: str = field(default_factory=_utc_now_iso)

    def model_dump(self) -> Dict[str, Any]:
        res = asdict(self)
        res["state"] = self.state.value if isinstance(self.state, HostStatusEnum) else str(self.state)
        if isinstance(self.apply_result, HostApplyResult):
            res["apply_result"] = self.apply_result.to_dict()
        return res

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostOperationStatus":
        state_val = data["state"]
        state_enum = HostStatusEnum(state_val) if isinstance(state_val, str) else state_val
        apply_res = data.get("apply_result")
        apply_obj = HostApplyResult.from_dict(apply_res) if isinstance(apply_res, dict) else apply_res
        return cls(
            state=state_enum,
            operation_id=data["operation_id"],
            idempotency_key=str(data.get("idempotency_key", "")),
            apply_result=apply_obj,
            authoritative=bool(data.get("authoritative", False)),
            details=dict(data.get("details", {})),
            queried_at=data.get("queried_at", _utc_now_iso()),
        )


@dataclass
class HostVerificationResult:
    """Host-level postcondition verification outcome."""
    operation_id: str
    verified: bool
    verified_revision: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None
    verified_at: str = field(default_factory=_utc_now_iso)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HostVerificationResult":
        return cls(
            operation_id=data["operation_id"],
            verified=bool(data["verified"]),
            verified_revision=str(data.get("verified_revision", "")),
            evidence=dict(data.get("evidence", {})),
            reason=data.get("reason"),
            verified_at=data.get("verified_at", _utc_now_iso()),
        )


@runtime_checkable
class HostAdapter(Protocol):
    """
    Universal host adapter protocol implemented by all hosts.
    Blender adapter uses bpy; test host uses durable filesystem state.
    """

    def inspect_document(self, request: InspectionRequest) -> InspectionResult:
        """Inspect document state (strictly read-only)."""
        ...

    def prepare_operation(self, operation: HostOperationRequest) -> PreparedHostOperation:
        """Validate preconditions on host (strictly read-only)."""
        ...

    def apply_operation(self, operation: HostOperationRequest) -> HostApplyResult:
        """Apply mutation on host and persist host-side execution record."""
        ...

    def query_operation_status(self, operation_id: str, idempotency_key: str) -> HostOperationStatus:
        """Query host for durable status of an operation (used after ACK loss or crash)."""
        ...

    def verify_operation(self, operation: HostOperationRequest, apply_result: HostApplyResult) -> HostVerificationResult:
        """Verify postconditions on host against durable host state."""
        ...
