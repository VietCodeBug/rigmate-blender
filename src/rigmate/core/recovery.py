"""Crash recovery scanner, reconciliation, and recovery decision model.

Features:
- Scans .rigmate/jobs/ on startup for non-terminal jobs
- Validates sequence gaps, journal corruptions, and missing receipts
- Evaluates whether unacknowledged mutation already executed on host (via query_status)
- Avoids blind retries and generates durable recovery.json records
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.events import RigMateEvent
from rigmate.core.executors import OperationExecutor
from rigmate.core.host_protocol import HostAdapter, HostApplyResult, HostStatusEnum
from rigmate.core.jobs import JobRecord, JobStatus, is_terminal_status
from rigmate.core.receipts import OperationReceipt, ReceiptError, ReceiptStatus
from rigmate.core.time_utils import to_utc_iso
from rigmate.storage.job_store import JobStore


class RecoveryAction(str, Enum):
    SAFE_TO_RESUME_OR_CANCEL = "safe_to_resume_or_cancel"
    RESUME_VERIFICATION = "resume_verification"
    QUERY_HOST_STATUS = "query_host_status"
    REQUIRE_RECOVERY = "require_recovery"
    RESTORE_FROM_CHECKPOINT = "restore_from_checkpoint"
    MANUAL_INSPECTION = "manual_inspection"


class RecoveryDecision(BaseModel):
    job_id: str
    detected_at: str = Field(default_factory=to_utc_iso)
    job_status_at_detection: JobStatus
    operation_id: Optional[str] = None
    apply_started: bool = False
    receipt_present: bool = False
    host_status: Optional[str] = None
    recommended_action: str = RecoveryAction.SAFE_TO_RESUME_OR_CANCEL.value
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


def reconcile_job_events(job: JobRecord, events: List[RigMateEvent]) -> None:
    """
    Validate sequence continuity, replay state, and enforce consistency
    between event journal and materialized job.
    Raises RigMateError(EVENT_SEQUENCE_INVALID) or (JOURNAL_INCONSISTENT) if gap or regression detected.
    """
    if not events:
        return

    # Check monotonic sequences starting from 0 or initial
    expected_seq = 0
    replayed_status = None
    event_types = set()

    for ev in events:
        if ev.sequence != expected_seq:
            raise RigMateError(
                f"Event sequence gap detected for job '{job.job_id}': expected sequence {expected_seq}, found {ev.sequence}",
                code=RigMateErrorCode.EVENT_SEQUENCE_INVALID,
                details={"job_id": job.job_id, "expected": expected_seq, "actual": ev.sequence},
            )
        expected_seq += 1
        event_types.add(ev.event_type)
        if "to_status" in ev.payload:
            replayed_status = JobStatus(ev.payload["to_status"])

    last_event = events[-1]

    # Reconstruct materialized status if journal is ahead
    if replayed_status is not None and replayed_status != job.status:
        # Journal is ahead of materialized state (e.g. crash after journal write)
        job.status = replayed_status

    if job.last_event_sequence != -1 and job.last_event_sequence < last_event.sequence:
        job.last_event_sequence = last_event.sequence

    # Consistency checks: completed / recovered must have journal proof
    if job.status == JobStatus.COMPLETED and "job.completed" not in event_types:
        raise RigMateError(
            f"Job '{job.job_id}' materialized status is 'completed' but journal lacks 'job.completed' event",
            code=RigMateErrorCode.JOURNAL_INCONSISTENT,
            details={"job_id": job.job_id, "status": job.status.value},
        )
    if job.status == JobStatus.RECOVERED and "job.recovered" not in event_types:
        raise RigMateError(
            f"Job '{job.job_id}' materialized status is 'recovered' but journal lacks 'job.recovered' event",
            code=RigMateErrorCode.JOURNAL_INCONSISTENT,
            details={"job_id": job.job_id, "status": job.status.value},
        )



class RecoveryScanner:
    """
    Scans storage for non-terminal jobs and orchestrates startup recovery.
    """

    def __init__(self, store: JobStore, executor: Optional[Union[HostAdapter, OperationExecutor]] = None):
        self.store = store
        self.executor = executor

    def scan_and_reconcile(self) -> List[RecoveryDecision]:
        """
        Scan all jobs, validate journals, detect interrupted states, and generate decisions.
        Surfaces corrupted job directories as actionable forensic decisions.
        """
        decisions: List[RecoveryDecision] = []

        # 1. Retrieve valid and corrupt jobs
        if hasattr(self.store, "list_jobs_and_corrupt"):
            valid_jobs, corrupt_records = self.store.list_jobs_and_corrupt()
            for c in corrupt_records:
                decisions.append(
                    RecoveryDecision(
                        job_id=c.job_id,
                        job_status_at_detection=JobStatus.RECOVERY_REQUIRED,
                        recommended_action=RecoveryAction.MANUAL_INSPECTION.value,
                        reason=f"Corrupt job metadata in '{c.job_dir}': {c.message}",
                        evidence={"error_code": c.error_code, "job_dir": c.job_dir},
                    )
                )
        else:
            valid_jobs = self.store.list_jobs()

        # 2. Process valid jobs
        for job in valid_jobs:
            if is_terminal_status(job.status):
                continue

            orig_status = job.status
            orig_seq = job.last_event_sequence

            events = self.store.read_events(job.job_id, tolerate_truncated_final=True)
            reconcile_job_events(job, events)

            # Persist corrected materialized state if replay altered status or sequence
            if job.status != orig_status or job.last_event_sequence != orig_seq:
                self.store.save_job(job)

            decision = self._classify_job(job)
            decisions.append(decision)

            # Persist recovery decision record
            self.store.save_recovery_record(job.job_id, decision.model_dump())

        return decisions

    def _classify_job(self, job: JobRecord) -> RecoveryDecision:
        # 1. Prepared: Safe to resume or cancel before any mutation
        if job.status in {JobStatus.QUEUED, JobStatus.INSPECTING, JobStatus.NEEDS_INPUT, JobStatus.PREPARED}:
            return RecoveryDecision(
                job_id=job.job_id,
                job_status_at_detection=job.status,
                operation_id=job.current_operation_id,
                apply_started=False,
                receipt_present=False,
                recommended_action=RecoveryAction.SAFE_TO_RESUME_OR_CANCEL.value,
                reason=f"Job was in pre-mutation state '{job.status.value}'. No side-effects initiated.",
            )

        # 2. Applying: Need to discover whether host executed mutation
        if job.status in {JobStatus.APPLYING, JobStatus.CANCEL_REQUESTED}:
            op_id = job.current_operation_id
            receipt = self.store.load_receipt(job.job_id, op_id) if op_id else None

            if receipt:
                # Receipt already existed locally, crash occurred before job status update
                return RecoveryDecision(
                    job_id=job.job_id,
                    job_status_at_detection=job.status,
                    operation_id=op_id,
                    apply_started=True,
                    receipt_present=True,
                    recommended_action=RecoveryAction.RESUME_VERIFICATION.value,
                    reason="Operation receipt is present on disk. Ready to verify outcome.",
                    evidence={"receipt_status": receipt.status.value},
                )

            # No local receipt: query executor or host adapter if available
            host_receipt = None
            host_status_str = "unknown"
            if self.executor and op_id:
                op = self.store.load_operation(job.job_id, op_id)
                key = op.idempotency_key if op else ""
                if isinstance(self.executor, HostAdapter):
                    status = self.executor.query_operation_status(op_id, key)
                    host_status_str = status.state.value if hasattr(status.state, "value") else str(status.state)
                    if status.state == HostStatusEnum.EXECUTED and status.apply_result:
                        apply_res = status.apply_result
                        host_receipt = OperationReceipt(
                            operation_id=apply_res.operation_id,
                            status=ReceiptStatus.COMPLETED,
                            host_revision_before=apply_res.host_revision_before,
                            host_revision_after=apply_res.host_revision_after,
                            facts=apply_res.facts,
                            changes=apply_res.changes,
                            verified_at=to_utc_iso(),
                        )
                    elif status.state == HostStatusEnum.NOT_FOUND:
                        return RecoveryDecision(
                            job_id=job.job_id,
                            job_status_at_detection=job.status,
                            operation_id=op_id,
                            apply_started=True,
                            receipt_present=False,
                            host_status="not_found",
                            recommended_action=RecoveryAction.SAFE_TO_RESUME_OR_CANCEL.value,
                            reason="Host authoritatively proves operation was never accepted or executed. Safe to redispatch.",
                        )
                elif hasattr(self.executor, "query_status"):
                    host_receipt = self.executor.query_status(op_id, key)

            if host_receipt:
                # Host already completed mutation: save receipt locally and resume verification
                self.store.save_receipt(job.job_id, host_receipt)
                return RecoveryDecision(
                    job_id=job.job_id,
                    job_status_at_detection=job.status,
                    operation_id=op_id,
                    apply_started=True,
                    receipt_present=True,
                    host_status="mutation_acknowledged_by_host",
                    recommended_action=RecoveryAction.RESUME_VERIFICATION.value,
                    reason="Host confirmed mutation occurred. Saved receipt locally; proceed to verify.",
                    evidence={"host_revision_after": host_receipt.host_revision_after},
                )
            else:
                # Uncertain or unavailable status: mutation might have executed, cannot blindly replay
                return RecoveryDecision(
                    job_id=job.job_id,
                    job_status_at_detection=job.status,
                    operation_id=op_id,
                    apply_started=True,
                    receipt_present=False,
                    host_status=host_status_str,
                    recommended_action=RecoveryAction.REQUIRE_RECOVERY.value,
                    reason="Apply was started but neither local receipt nor host status could be confirmed. Manual recovery required.",
                )

        # 3. Verifying
        if job.status == JobStatus.VERIFYING:
            return RecoveryDecision(
                job_id=job.job_id,
                job_status_at_detection=job.status,
                operation_id=job.current_operation_id,
                apply_started=True,
                receipt_present=True,
                recommended_action=RecoveryAction.RESUME_VERIFICATION.value,
                reason="Job crashed during postcondition verification. Re-verify.",
            )

        # 4. Recovery Required
        return RecoveryDecision(
            job_id=job.job_id,
            job_status_at_detection=job.status,
            operation_id=job.current_operation_id,
            apply_started=True,
            receipt_present=False,
            recommended_action=RecoveryAction.RESTORE_FROM_CHECKPOINT.value,
            reason="Job is flagged recovery_required. Restore authorized files from checkpoint.",
        )

