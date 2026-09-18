"""Durable filesystem-backed fake host adapter for headless control plane testing.

Simulates a real separate host process (like Blender or Godot) with:
- Independent persistent state in a designated host state directory
- Document revisions, objects, facts, and mutation counts stored on disk
- Host-side idempotency registry and operation result tracking
- Simulated faults:
  - ACK loss (host mutates and persists state, then drops connection before acknowledging)
  - Stale revision rejection (TARGET_STALE)
  - Postcondition verification failure
  - Host unavailable
  - Host unknown state
- Pure Python stdlib + Contracts (NO bpy, NO FastAPI, NO network)
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rigmate.contracts.hashing import compute_operation_request_hash
from rigmate.contracts.host import (
    DocumentIdentity,
    HostAdapter,
    HostApplyResult,
    HostIdentity,
    HostOperationExecutionState,
    HostOperationRequest,
    HostOperationStatus,
    HostStatusEnum,
    HostType,
    HostVerificationResult,
    InspectionRequest,
    InspectionResult,
    PreparedHostOperation,
)
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.ids import validate_safe_id
from rigmate.core.path_safety import require_within_root
from rigmate.core.receipts import OperationReceipt, ReceiptStatus
from rigmate.core.time_utils import to_utc_iso


ALLOWED_TOOLS = {
    "object.rename",
    "document.set_test_value",
    "armature.bone_fix",
    "armature.align",
    "checkpoint.create",
}


class DurableFakeHost:
    """
    Filesystem-backed durable fake host implementing HostAdapter.
    Survives destruction and re-instantiation of Python objects.
    """

    def __init__(
        self,
        host_state_dir: Union[str, Path],
        host_instance_id: str = "host_1",
        initial_revision: str = "rev_1",
        next_revision: str = "rev_2",
        simulate_ack_loss: bool = False,
        simulate_stale_revision: bool = False,
        simulate_verify_failure: bool = False,
        simulate_host_unavailable: bool = False,
        simulate_host_unknown: bool = False,
    ):
        self.state_dir = Path(host_state_dir).resolve()
        self.host_instance_id = validate_safe_id(host_instance_id, "host_instance_id")
        self.initial_revision = initial_revision
        self.next_revision = next_revision

        self.simulate_ack_loss = simulate_ack_loss
        self.simulate_stale_revision = simulate_stale_revision
        self.simulate_verify_failure = simulate_verify_failure
        self.simulate_host_unavailable = simulate_host_unavailable
        self.simulate_host_unknown = simulate_host_unknown

        # Subdirectories
        self.docs_dir = self.state_dir / "documents"
        self.ops_dir = self.state_dir / "operations"
        self.idem_dir = self.state_dir / "idempotency"

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.ops_dir.mkdir(parents=True, exist_ok=True)
        self.idem_dir.mkdir(parents=True, exist_ok=True)

        self._init_host_metadata()

    def _init_host_metadata(self) -> None:
        """Write or verify host.json in state dir."""
        h_file = self.state_dir / "host.json"
        if not h_file.is_file():
            meta = HostIdentity(
                host_instance_id=self.host_instance_id,
                host_type=HostType.FAKE.value,
                protocol_version="1.0.0",
            )
            self._write_json_atomic(h_file, meta.model_dump())

    def _doc_file(self, document_id: str) -> Path:
        safe_id = validate_safe_id(document_id, "document_id")
        target = self.docs_dir / f"{safe_id}.json"
        return require_within_root(target, self.docs_dir)

    def _op_file(self, operation_id: str) -> Path:
        safe_id = validate_safe_id(operation_id, "operation_id")
        target = self.ops_dir / f"{safe_id}.json"
        return require_within_root(target, self.ops_dir)

    def _idem_file(self, idempotency_key: str) -> Path:
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        target = self.idem_dir / f"{key_hash}.json"
        return require_within_root(target, self.idem_dir)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_json_atomic(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".tmp.{Path(__file__).stem}_{id(data)}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        tmp.replace(path)

    def get_or_create_document(self, document_id: str, default_revision: Optional[str] = None) -> Dict[str, Any]:
        """Load document state from disk or create initial document."""
        doc_file = self._doc_file(document_id)
        if doc_file.is_file():
            return self._read_json(doc_file)

        doc = {
            "document_id": document_id,
            "project_id": "proj_1",
            "current_revision": default_revision or self.initial_revision,
            "mutation_count": 0,
            "objects": {
                "Character": {
                    "name": "Character",
                    "type": "mesh",
                    "vertex_count": 50000,
                    "has_armature": True,
                },
                "Armature": {
                    "name": "Armature",
                    "type": "armature",
                    "bone_count": 54,
                },
            },
            "custom_properties": {},
            "updated_at": to_utc_iso(),
        }
        self.save_document(doc)
        return doc

    def save_document(self, doc: Dict[str, Any]) -> None:
        """Persist document state to disk."""
        doc["updated_at"] = to_utc_iso()
        self._write_json_atomic(self._doc_file(doc["document_id"]), doc)

    @property
    def mutation_count(self) -> int:
        """Get aggregate mutation count for primary test document."""
        doc = self.get_or_create_document("doc_1")
        return doc.get("mutation_count", 0)

    @property
    def current_revision(self) -> str:
        """Get current revision for primary test document."""
        doc = self.get_or_create_document("doc_1")
        return doc.get("current_revision", self.initial_revision)

    # --- HostAdapter Implementation ---

    def inspect_document(self, request: InspectionRequest) -> InspectionResult:
        """Inspect document state (strictly read-only)."""
        if self.simulate_host_unavailable:
            raise RigMateError("Host unavailable", code=RigMateErrorCode.HOST_UNAVAILABLE)

        doc = self.get_or_create_document(request.document_id)
        return InspectionResult(
            document=DocumentIdentity(
                project_id=request.project_id,
                document_id=request.document_id,
                revision=doc["current_revision"],
            ),
            facts={"mutation_count": doc["mutation_count"]},
            scene_objects=list(doc["objects"].values()),
        )

    def prepare_operation(self, operation: Union[HostOperationRequest, Any]) -> PreparedHostOperation:
        """Validate preconditions on host (strictly read-only)."""
        if self.simulate_host_unavailable:
            raise RigMateError("Host unavailable", code=RigMateErrorCode.HOST_UNAVAILABLE)

        doc = self.get_or_create_document(operation.document_id)

        if self.simulate_stale_revision or operation.expected_revision != doc["current_revision"]:
            raise RigMateError(
                f"Host revision '{doc['current_revision']}' does not match expected '{operation.expected_revision}'",
                code=RigMateErrorCode.TARGET_STALE,
                details={
                    "current_revision": doc["current_revision"],
                    "expected_revision": operation.expected_revision,
                },
            )

        if operation.tool not in ALLOWED_TOOLS:
            raise RigMateError(
                f"Tool '{operation.tool}' not supported by host",
                code=RigMateErrorCode.VALIDATION_FAILED,
                details={"tool": operation.tool, "allowed": sorted(list(ALLOWED_TOOLS))},
            )

        mode_val = operation.mode.value if hasattr(operation.mode, "value") else str(operation.mode)

        return PreparedHostOperation(
            operation_id=operation.operation_id,
            document=DocumentIdentity(
                project_id=operation.project_id,
                document_id=operation.document_id,
                revision=doc["current_revision"],
            ),
            tool=operation.tool,
            mode=mode_val,
            can_apply=True,
        )

    def apply_operation(self, operation: Union[HostOperationRequest, Any]) -> HostApplyResult:
        """Apply mutation on host and persist host-side execution record."""
        if self.simulate_host_unavailable:
            raise RigMateError("Host unavailable", code=RigMateErrorCode.HOST_UNAVAILABLE)

        req_hash = compute_operation_request_hash(operation)
        idem_file = self._idem_file(operation.idempotency_key)

        # 1. Host-side idempotency check
        if idem_file.is_file():
            idem_data = self._read_json(idem_file)
            if idem_data.get("request_hash") != req_hash:
                raise RigMateError(
                    f"Host idempotency conflict: key '{operation.idempotency_key}' used with different request hash",
                    code=RigMateErrorCode.IDEMPOTENCY_CONFLICT,
                    details={
                        "idempotency_key": operation.idempotency_key,
                        "existing_hash": idem_data.get("request_hash"),
                        "new_hash": req_hash,
                    },
                )
            # Replay: return persisted apply_result without re-mutating!
            cached_result = HostApplyResult.from_dict(idem_data["apply_result"])
            return cached_result

        # 2. Check document revision
        doc = self.get_or_create_document(operation.document_id)
        if self.simulate_stale_revision or operation.expected_revision != doc["current_revision"]:
            raise RigMateError(
                f"Host revision '{doc['current_revision']}' does not match expected '{operation.expected_revision}'",
                code=RigMateErrorCode.TARGET_STALE,
                details={
                    "current_revision": doc["current_revision"],
                    "expected_revision": operation.expected_revision,
                },
            )

        # 3. Perform deterministic mutation on document state
        rev_before = doc["current_revision"]
        rev_after = self.next_revision if self.next_revision != rev_before else f"{rev_before}_next"

        changes: List[Dict[str, Any]] = []
        target_ids = list(operation.target_ids) if operation.target_ids else []
        arguments = dict(operation.arguments) if operation.arguments else {}

        if operation.tool == "object.rename":
            target = target_ids[0] if target_ids else "Character"
            new_name = arguments.get("new_name", f"{target}_Renamed")
            if target in doc["objects"]:
                obj_data = doc["objects"].pop(target)
                obj_data["name"] = new_name
                doc["objects"][new_name] = obj_data
                changes.append({"target": target, "action": "renamed", "new_name": new_name})
        elif operation.tool == "document.set_test_value":
            k = arguments.get("key", "test_key")
            v = arguments.get("value", "test_value")
            doc["custom_properties"][k] = v
            changes.append({"target": k, "action": "set_value", "value": v})
        else:
            for t in target_ids:
                changes.append({"target": t, "action": f"fake_applied_{operation.tool}"})

        doc["mutation_count"] += 1
        doc["current_revision"] = rev_after
        self.save_document(doc)

        apply_result = HostApplyResult(
            operation_id=operation.operation_id,
            execution_state=HostOperationExecutionState.APPLIED.value,
            host_revision_before=rev_before,
            host_revision_after=rev_after,
            facts={"mutation_count": doc["mutation_count"], "mutated_targets": target_ids},
            changes=changes,
            executed_at=to_utc_iso(),
        )

        # 4. Host durably records operation status and idempotency before acknowledging
        op_record = {
            "operation_id": operation.operation_id,
            "idempotency_key": operation.idempotency_key,
            "request_hash": req_hash,
            "apply_result": apply_result.model_dump(),
            "created_at": to_utc_iso(),
        }
        self._write_json_atomic(self._op_file(operation.operation_id), op_record)
        self._write_json_atomic(idem_file, op_record)

        # 5. Fault injection: ACK loss simulation
        if self.simulate_ack_loss:
            self.simulate_ack_loss = False  # Fire once
            raise ConnectionResetError("Simulated network ACK loss: host mutated and persisted state, but ACK was dropped")

        return apply_result

    def query_operation_status(self, operation_id: str, idempotency_key: str) -> HostOperationStatus:
        """
        Query host for durable status of an operation from disk.
        Returns explicit HostOperationStatus distinguishing EXECUTED, NOT_FOUND, UNKNOWN, UNAVAILABLE.
        """
        if self.simulate_host_unavailable:
            return HostOperationStatus(
                state=HostStatusEnum.UNAVAILABLE,
                operation_id=operation_id,
                idempotency_key=idempotency_key,
                authoritative=False,
                details={"reason": "Host is simulated as unavailable/offline"},
            )

        if self.simulate_host_unknown:
            return HostOperationStatus(
                state=HostStatusEnum.UNKNOWN,
                operation_id=operation_id,
                idempotency_key=idempotency_key,
                authoritative=False,
                details={"reason": "Host state is simulated as ambiguous/unknown"},
            )

        # Check by operation_id
        if operation_id:
            try:
                op_file = self._op_file(operation_id)
                if op_file.is_file():
                    data = self._read_json(op_file)
                    apply_res = HostApplyResult.from_dict(data["apply_result"])
                    return HostOperationStatus(
                        state=HostStatusEnum.EXECUTED,
                        operation_id=operation_id,
                        idempotency_key=idempotency_key,
                        apply_result=apply_res,
                        authoritative=True,
                    )
            except Exception as e:
                return HostOperationStatus(
                    state=HostStatusEnum.UNKNOWN,
                    operation_id=operation_id,
                    idempotency_key=idempotency_key,
                    authoritative=False,
                    details={"error": str(e)},
                )

        # Check by idempotency_key
        if idempotency_key:
            try:
                idem_file = self._idem_file(idempotency_key)
                if idem_file.is_file():
                    data = self._read_json(idem_file)
                    apply_res = HostApplyResult.from_dict(data["apply_result"])
                    return HostOperationStatus(
                        state=HostStatusEnum.EXECUTED,
                        operation_id=data.get("operation_id", operation_id),
                        idempotency_key=idempotency_key,
                        apply_result=apply_res,
                        authoritative=True,
                    )
            except Exception as e:
                return HostOperationStatus(
                    state=HostStatusEnum.UNKNOWN,
                    operation_id=operation_id,
                    idempotency_key=idempotency_key,
                    authoritative=False,
                    details={"error": str(e)},
                )

        # Authoritative proof: registry was searched and operation is absent
        return HostOperationStatus(
            state=HostStatusEnum.NOT_FOUND,
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            authoritative=True,
            details={"reason": "Operation not present in host operations or idempotency registry"},
        )

    def verify_operation(self, operation: Union[HostOperationRequest, Any], apply_result: HostApplyResult) -> HostVerificationResult:
        """Verify postconditions on host against durable host state on disk."""
        if self.simulate_verify_failure:
            return HostVerificationResult(
                operation_id=operation.operation_id,
                verified=False,
                verified_revision=apply_result.host_revision_after,
                evidence={"reason": "Simulated postcondition failure"},
                reason="Simulated verification failure",
            )

        doc = self.get_or_create_document(operation.document_id)
        if doc["current_revision"] != apply_result.host_revision_after:
            return HostVerificationResult(
                operation_id=operation.operation_id,
                verified=False,
                verified_revision=doc["current_revision"],
                evidence={"expected_revision": apply_result.host_revision_after, "actual_revision": doc["current_revision"]},
                reason=f"Revision mismatch during verification (expected {apply_result.host_revision_after}, found {doc['current_revision']})",
            )

        return HostVerificationResult(
            operation_id=operation.operation_id,
            verified=True,
            verified_revision=doc["current_revision"],
            evidence={"mutation_count": doc["mutation_count"], "changes_verified": len(apply_result.changes)},
        )

    # --- Backwards-compatible OperationExecutor methods ---

    def prepare(self, operation: Any) -> bool:
        res = self.prepare_operation(operation)
        return res.can_apply

    def apply(self, operation: Any) -> OperationReceipt:
        res = self.apply_operation(operation)
        return OperationReceipt(
            operation_id=res.operation_id,
            status=ReceiptStatus.COMPLETED,
            host_revision_before=res.host_revision_before,
            host_revision_after=res.host_revision_after,
            facts=res.facts,
            changes=res.changes,
            verified_at=to_utc_iso(),
        )

    def verify(self, operation: Any, receipt: OperationReceipt) -> bool:
        apply_res = HostApplyResult(
            operation_id=receipt.operation_id,
            host_revision_before=receipt.host_revision_before,
            host_revision_after=receipt.host_revision_after or receipt.host_revision_before,
            facts=receipt.facts,
            changes=receipt.changes,
        )
        ver_res = self.verify_operation(operation, apply_res)
        return ver_res.verified

    def query_status(self, operation_id: str, idempotency_key: str) -> Optional[OperationReceipt]:
        status = self.query_operation_status(operation_id, idempotency_key)
        if status.state == HostStatusEnum.EXECUTED and status.apply_result:
            return OperationReceipt(
                operation_id=status.apply_result.operation_id,
                status=ReceiptStatus.COMPLETED,
                host_revision_before=status.apply_result.host_revision_before,
                host_revision_after=status.apply_result.host_revision_after,
                facts=status.apply_result.facts,
                changes=status.apply_result.changes,
                verified_at=to_utc_iso(),
            )
        return None
