"""Job lifecycle service for RigMate V1.

Orchestrates:
- create_job
- start_inspecting
- prepare_job (validates plan, preconditions, acquires checkpoint)
- start_apply (acquires lock, re-checks revision, records intent, applies, records receipt, verifies)
- request_cancel (idempotent, safe cancellation before apply, cancel_requested during apply)
- verify_job (checks postconditions, completes job or transitions to recovery_required)
- recover_job (restores checkpoint to non-destructive copy, verifies hashes, transitions to recovered)
- build_timeline (generates debug trace)
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from rigmate.core.checkpoints import CheckpointManifest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.events import RigMateEvent
from rigmate.core.executors import OperationExecutor
from rigmate.core.ids import new_event_id, new_job_id, new_correlation_id, new_checkpoint_id
from rigmate.core.jobs import (
    JobRecord,
    JobStatus,
    JobType,
    is_terminal_status,
    validate_transition,
)
from rigmate.core.lock import DocumentLock
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.core.plans import PreparedPlan
from rigmate.core.receipts import OperationReceipt, ReceiptError, ReceiptStatus
from rigmate.core.time_utils import to_utc_iso
from rigmate.core.timeline import TimelineEntry, build_job_timeline
from rigmate.storage.checkpoints import CheckpointEngine
from rigmate.storage.idempotency import IdempotencyRegistry
from rigmate.storage.job_store import JobStore


class JobService:
    """
    Core service orchestrating job lifecycle, state transitions, journals, and execution.
    """

    def __init__(
        self,
        storage_root: Union[str, Path],
        project_root: Union[str, Path],
        executor: OperationExecutor,
        fault_hook: Optional[Callable[[str, Any], None]] = None,
    ):
        self.storage_root = Path(storage_root).resolve()
        self.project_root = Path(project_root).resolve()
        self.executor = executor
        self.fault_hook = fault_hook  # Test fault injection hook (hook_name, context)

        self.store = JobStore(self.storage_root)
        self.checkpoint_engine = CheckpointEngine(self.storage_root)
        self.idempotency = IdempotencyRegistry(self.storage_root)
        self.lock_dir = self.storage_root / "locks"

    def _trigger_fault(self, hook_name: str, context: Any = None) -> None:
        if self.fault_hook:
            self.fault_hook(hook_name, context)

    def _emit_event(
        self,
        job: JobRecord,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> RigMateEvent:
        """Append monotonic event to journal and advance sequence."""
        seq = job.last_event_sequence + 1
        ev = RigMateEvent(
            event_id=new_event_id(),
            sequence=seq,
            timestamp=to_utc_iso(),
            event_type=event_type,
            project_id=job.project_id,
            job_id=job.job_id,
            correlation_id=job.correlation_id,
            payload=payload or {},
        )
        self.store.append_event(ev)
        job.last_event_sequence = seq
        job.updated_at = ev.timestamp
        return ev

    def _transition_job(
        self,
        job: JobRecord,
        target_status: JobStatus,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        terminal_reason: Optional[str] = None,
        error: Optional[ReceiptError] = None,
    ) -> None:
        """Validate transition, emit event, and atomically persist job.json."""
        validate_transition(job.status, target_status)
        prev_status = job.status
        job.status = target_status
        if terminal_reason:
            job.terminal_reason = terminal_reason
        if error:
            job.error = error

        p = dict(payload or {})
        p["from_status"] = prev_status.value
        p["to_status"] = target_status.value
        if error:
            p["error_code"] = error.code

        # Append to journal first
        self._emit_event(job, event_type, p)

        # Fault injection hook: right after journal write, before materialized state
        self._trigger_fault("after_journal_before_job_json", job)

        # Atomically update materialized job state
        self.store.save_job(job)

    def create_job(
        self,
        project_id: str,
        host_instance_id: str,
        document_id: str,
        expected_revision: str,
        job_type: JobType = JobType.MUTATION,
        correlation_id: Optional[str] = None,
        requested_by: str = "user",
    ) -> JobRecord:
        """Create and persist a new job in queued state."""
        jid = new_job_id()
        cid = correlation_id or new_correlation_id()
        now = to_utc_iso()

        job = JobRecord(
            job_id=jid,
            project_id=project_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            correlation_id=cid,
            requested_by=requested_by,
            host_instance_id=host_instance_id,
            document_id=document_id,
            expected_revision=expected_revision,
            last_event_sequence=-1,
        )

        # Initial event & save
        self._emit_event(
            job,
            "job.created",
            {
                "job_type": job_type.value,
                "document_id": document_id,
                "expected_revision": expected_revision,
            },
        )
        self.store.save_job(job)
        return job

    def get_job(self, job_id: str) -> JobRecord:
        """Retrieve job record."""
        return self.store.load_job(job_id)

    def start_inspecting(self, job_id: str) -> JobRecord:
        """Transition job to inspecting state."""
        job = self.get_job(job_id)
        self._transition_job(job, JobStatus.INSPECTING, "job.inspect_started")
        return job

    def prepare_job(
        self,
        job_id: str,
        plan: PreparedPlan,
        checkpoint_source_files: Optional[List[Union[str, Path]]] = None,
    ) -> JobRecord:
        """
        Prepare job:
        1. Persist prepared plan.
        2. Create checkpoint if required and files specified.
        3. Transition to prepared state.
        """
        job = self.get_job(job_id)

        # Verify revision precondition
        if plan.expected_revision != job.expected_revision:
            raise RigMateError(
                f"Plan revision '{plan.expected_revision}' does not match job expected revision '{job.expected_revision}'",
                code=RigMateErrorCode.TARGET_STALE,
            )

        # Persist plan
        self.store.save_plan(plan)
        job.plan_ref = plan.plan_id

        # Acquire checkpoint if required
        if plan.checkpoint_required and checkpoint_source_files:
            cp_id = new_checkpoint_id()
            self._emit_event(job, "checkpoint.requested", {"checkpoint_id": cp_id})

            self._trigger_fault("before_checkpoint_create", cp_id)
            manifest = self.checkpoint_engine.create_checkpoint(
                checkpoint_id=cp_id,
                project_id=job.project_id,
                job_id=job.job_id,
                project_root=self.project_root,
                file_paths=checkpoint_source_files,
                source_revision=job.expected_revision,
                reason=f"Pre-mutation checkpoint for job {job.job_id}",
            )
            job.checkpoint_ref = cp_id
            self._emit_event(
                job,
                "checkpoint.created",
                {"checkpoint_id": cp_id, "files": [f.relative_path for f in manifest.files]},
            )

        self._transition_job(
            job,
            JobStatus.PREPARED,
            "job.prepared",
            {"plan_id": plan.plan_id, "checkpoint_id": job.checkpoint_ref},
        )
        return job

    def start_apply(self, job_id: str, operation: OperationEnvelope) -> JobRecord:
        """
        Apply mutation operation under document single-writer lock.
        - Checks revision precondition
        - Enforces checkpoint requirement
        - Tracks operation idempotency
        - Simulates/handles ACK loss without blind replay
        - Automatically transitions to verifying or recovery_required
        """
        job = self.get_job(job_id)

        # Setup lock
        doc_lock = DocumentLock(
            lock_dir=self.lock_dir,
            project_id=job.project_id,
            host_instance_id=job.host_instance_id,
            document_id=job.document_id,
        )

        doc_lock.acquire(job.job_id)
        try:
            # Idempotency check: if already executed, return cached receipt immediately without mutating or failing
            existing_idem = self.idempotency.check(operation)
            if existing_idem and existing_idem.receipt:
                # Duplicate operation already executed; return without mutating again
                receipt = OperationReceipt(**existing_idem.receipt)
                self.store.save_receipt(job.job_id, receipt)
                if job.status == JobStatus.COMPLETED:
                    return job
                return self.verify_job(job.job_id, operation, receipt)

            # Revalidate revision precondition with host executor before apply
            if operation.expected_revision != job.expected_revision:
                raise RigMateError(
                    f"Operation expected revision '{operation.expected_revision}' does not match job expected revision '{job.expected_revision}'",
                    code=RigMateErrorCode.TARGET_STALE,
                )

            # Pre-flight host check
            self.executor.prepare(operation)

            # Check checkpoint requirement
            if operation.mode == OperationMode.APPLY and operation.tool != "checkpoint.create":
                if not job.checkpoint_ref:
                    raise RigMateError(
                        "Apply mode operation requires a completed checkpoint",
                        code=RigMateErrorCode.CHECKPOINT_REQUIRED,
                    )

            # Persist operation intent
            self.store.save_operation(operation)
            job.current_operation_id = operation.operation_id

            # Transition to applying
            self._transition_job(
                job,
                JobStatus.APPLYING,
                "operation.apply_started",
                {"operation_id": operation.operation_id, "tool": operation.tool},
            )

            # Register idempotency intent
            self.idempotency.register(operation)

            self._trigger_fault("after_apply_started_before_executor", operation)

            # Execute on host
            receipt: Optional[OperationReceipt] = None
            try:
                receipt = self.executor.apply(operation)
            except Exception as e:
                # Handle possible ACK-loss scenario
                self._emit_event(
                    job,
                    "operation.apply_interrupted",
                    {"error": str(e)},
                )

                # Query host for status to check if mutation actually occurred!
                host_receipt = self.executor.query_status(
                    operation.operation_id, operation.idempotency_key
                )
                if host_receipt:
                    # Host actually mutated! Save receipt and proceed
                    receipt = host_receipt
                else:
                    # Status unknown: must flag recovery_required rather than blind retrying!
                    self._transition_job(
                        job,
                        JobStatus.RECOVERY_REQUIRED,
                        "job.recovery_required",
                        {"reason": "Apply failed or dropped without proven host status"},
                        error=ReceiptError(
                            code=RigMateErrorCode.RESULT_UNVERIFIED,
                            message=f"Apply error with uncertain host mutation state: {e}",
                        ),
                    )
                    return job

            # Receipt was obtained
            self.store.save_receipt(job.job_id, receipt)
            self.idempotency.register(operation, receipt=receipt)
            self._emit_event(
                job,
                "operation.receipt_recorded",
                {"operation_id": operation.operation_id, "status": receipt.status.value},
            )

            self._trigger_fault("after_receipt_persisted_before_verifying", receipt)

            # Transition to verifying
            self._transition_job(
                job,
                JobStatus.VERIFYING,
                "job.verify_started",
                {"operation_id": operation.operation_id},
            )

            # Verify postconditions
            return self.verify_job(job.job_id, operation, receipt)

        finally:
            doc_lock.release(job.job_id)

    def verify_job(
        self,
        job_id: str,
        operation: OperationEnvelope,
        receipt: OperationReceipt,
    ) -> JobRecord:
        """Verify postconditions and transition to completed or recovery_required."""
        job = self.get_job(job_id)

        # Run verification predicate via executor
        verified = self.executor.verify(operation, receipt)

        self._trigger_fault("after_verify_before_completed", verified)

        if verified and receipt.status == ReceiptStatus.COMPLETED:
            self._emit_event(
                job,
                "job.verify_succeeded",
                {"operation_id": operation.operation_id},
            )
            self._transition_job(
                job,
                JobStatus.COMPLETED,
                "job.completed",
                {"operation_id": operation.operation_id},
                terminal_reason="Operation applied and verified successfully",
            )
        else:
            self._emit_event(
                job,
                "job.verify_failed",
                {"operation_id": operation.operation_id},
            )
            self._transition_job(
                job,
                JobStatus.RECOVERY_REQUIRED,
                "job.recovery_required",
                {"operation_id": operation.operation_id},
                error=ReceiptError(
                    code=RigMateErrorCode.RESULT_UNVERIFIED,
                    message="Operation postcondition verification failed",
                ),
            )

        return job

    def request_cancel(self, job_id: str, reason: str = "user requested") -> JobRecord:
        """
        Request job cancellation.
        - If before applying: immediately marks cancelled.
        - If during applying: marks cancel_requested (does not falsely mark cancelled if mutation active).
        - If terminal or cancel_requested: idempotent return.
        """
        job = self.get_job(job_id)

        if is_terminal_status(job.status):
            return job

        if job.status == JobStatus.CANCEL_REQUESTED:
            return job

        # Safe pre-mutation states
        if job.status in {JobStatus.QUEUED, JobStatus.INSPECTING, JobStatus.NEEDS_INPUT, JobStatus.PREPARED}:
            self._transition_job(
                job,
                JobStatus.CANCELLED,
                "job.cancelled",
                {"reason": reason},
                terminal_reason=f"Cancelled before mutation: {reason}",
            )
            return job

        # Mid-flight mutation: mark cancel_requested
        if job.status == JobStatus.APPLYING:
            job.cancel_requested = True
            self._transition_job(
                job,
                JobStatus.CANCEL_REQUESTED,
                "job.cancel_requested",
                {"reason": reason},
            )
            return job

        return job

    def recover_job(self, job_id: str) -> JobRecord:
        """
        Perform recovery for a job in recovery_required status.
        Restores preserved files from checkpoint to verified copy, verifies hashes,
        and marks job recovered.
        """
        job = self.get_job(job_id)
        if job.status != JobStatus.RECOVERY_REQUIRED:
            raise RigMateError(
                f"Cannot recover job with status '{job.status.value}'; must be in 'recovery_required'",
                code=RigMateErrorCode.INVALID_JOB_TRANSITION,
            )

        if not job.checkpoint_ref:
            raise RigMateError(
                f"Job '{job.job_id}' has no checkpoint_ref to recover from",
                code=RigMateErrorCode.CHECKPOINT_REQUIRED,
            )

        self._emit_event(
            job,
            "job.recovery_started",
            {"checkpoint_id": job.checkpoint_ref},
        )

        # Restore to verified copy
        restored = self.checkpoint_engine.restore_to_copy(
            checkpoint_id=job.checkpoint_ref,
            project_root=self.project_root,
        )

        self._transition_job(
            job,
            JobStatus.RECOVERED,
            "job.recovered",
            {"checkpoint_id": job.checkpoint_ref, "restored_copies": restored},
            terminal_reason="Preserved files restored to verified copies",
        )
        return job

    def build_timeline(self, job_id: str) -> List[TimelineEntry]:
        """Build structured timeline for debugging."""
        return build_job_timeline(job_id, self.store)
