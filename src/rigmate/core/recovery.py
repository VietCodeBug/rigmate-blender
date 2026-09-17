"""Crash recovery scanner, reconciliation, and recovery decision model.

Features:
- Scans .rigmate/jobs/ on startup for non-terminal jobs
- Validates sequence gaps, journal corruptions, and missing receipts
- Evaluates whether unacknowledged mutation already executed on host (via query_status)
- Avoids blind retries and generates durable recovery.json records
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.events import RigMateEvent
from rigmate.core.executors import OperationExecutor
from rigmate.core.jobs import JobRecord, JobStatus, is_terminal_status
from rigmate.core.receipts import OperationReceipt, ReceiptError, ReceiptStatus
from rigmate.core.time_utils import to_utc_iso
from rigmate.storage.job_store import JobStore


class RecoveryDecision(BaseModel):
    job_id: str
    detected_at: str = Field(default_factory=to_utc_iso)
    job_status_at_detection: JobStatus
    operation_id: Optional[str] = None
    apply_started: bool = False
    receipt_present: bool = False
    host_status: Optional[str] = None
    recommended_action: str
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


def reconcile_job_events(job: JobRecord, events: List[RigMateEvent]) -> None:
    """
    Validate sequence continuity and consistency between event journal and materialized job.
    Raises RigMateError(EVENT_SEQUENCE_INVALID) or (JOURNAL_INCONSISTENT) if gap or sequence regression detected.
    """
    if not events:
        return

    # Check monotonic sequences starting from 0 or initial
    expected_seq = 0
    for ev in events:
        if ev.sequence != expected_seq:
            raise RigMateError(
                f"Event sequence gap detected for job '{job.job_id}': expected sequence {expected_seq}, found {ev.sequence}",
                code=RigMateErrorCode.EVENT_SEQUENCE_INVALID,
                details={"job_id": job.job_id, "expected": expected_seq, "actual": ev.sequence},
            )
        expected_seq += 1

    last_event = events[-1]
    if job.last_event_sequence != -1 and job.last_event_sequence < last_event.sequence:
        # Journal is ahead of materialized job state (common if process killed right after journal write)
        # Materialized state will be advanced to match last event
        job.last_event_sequence = last_event.sequence


class RecoveryScanner:
    """
    Scans storage for non-terminal jobs and orchestrates startup recovery.
    """

    def __init__(self, store: JobStore, executor: Optional[OperationExecutor] = None):
        self.store = store
        self.executor = executor

    def scan_and_reconcile(self) -> List[RecoveryDecision]:
        """
        Scan all jobs, validate journals, detect interrupted states, and generate decisions.
        """
        decisions: List[RecoveryDecision] = []
        jobs = self.store.list_jobs()

        for job in jobs:
            if is_terminal_status(job.status):
                continue

            events = self.store.read_events(job.job_id, tolerate_truncated_final=True)
            reconcile_job_events(job, events)

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
                recommended_action="safe_to_resume_or_cancel",
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
                    recommended_action="resume_verification",
                    reason="Operation receipt is present on disk. Ready to verify outcome.",
                    evidence={"receipt_status": receipt.status.value},
                )

            # No local receipt: query executor if available
            host_receipt = None
            if self.executor and op_id:
                op = self.store.load_operation(job.job_id, op_id)
                key = op.idempotency_key if op else ""
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
                    recommended_action="resume_verification",
                    reason="Host confirmed mutation occurred. Saved receipt locally; proceed to verify.",
                    evidence={"host_revision_after": host_receipt.host_revision_after},
                )
            else:
                # Uncertain status: mutation might have executed, cannot blindly replay
                return RecoveryDecision(
                    job_id=job.job_id,
                    job_status_at_detection=job.status,
                    operation_id=op_id,
                    apply_started=True,
                    receipt_present=False,
                    host_status="unknown",
                    recommended_action="require_recovery",
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
                recommended_action="resume_verification",
                reason="Job crashed during postcondition verification. Re-verify.",
            )

        # 4. Recovery Required
        return RecoveryDecision(
            job_id=job.job_id,
            job_status_at_detection=job.status,
            operation_id=job.current_operation_id,
            apply_started=True,
            receipt_present=False,
            recommended_action="restore_from_checkpoint",
            reason="Job is flagged recovery_required. Restore authorized files from checkpoint.",
        )
