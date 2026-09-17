"""Durable filesystem storage for RigMate jobs.

Layout:
  <storage_root>/jobs/<job_id>/
    job.json
    plan.json
    events.jsonl
    operations/<operation_id>.json
    receipts/<operation_id>.json
    recovery.json

Guarantees:
- Atomic replacement of materialized job state (job.json)
- Monotonic, crash-tolerant append of event journal (events.jsonl)
- Independent inspectability of operations, receipts, and plans
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.events import RigMateEvent
from rigmate.core.ids import validate_safe_id
from rigmate.core.jobs import JobRecord
from rigmate.core.operations import OperationEnvelope
from rigmate.core.path_safety import require_within_root
from rigmate.core.plans import PreparedPlan
from rigmate.core.receipts import OperationReceipt
from rigmate.storage.json_io import (
    append_jsonl,
    iter_jsonl,
    read_json,
    write_json_atomic,
)


@dataclass
class CorruptJobRecord:
    """Record of a discovered corrupted job directory or file."""
    job_id: str
    job_dir: str
    error_code: str
    message: str


class JobStore:
    """
    Filesystem repository managing persisted job state, plans, journals, operations, and receipts.
    """

    def __init__(self, storage_root: Union[str, Path]):
        self.storage_root = Path(storage_root).resolve()
        self.jobs_dir = self.storage_root / "jobs"

    def _job_dir(self, job_id: str) -> Path:
        safe_id = validate_safe_id(job_id, "job_id")
        target = self.jobs_dir / safe_id
        return require_within_root(target, self.jobs_dir)

    def save_job(self, job: JobRecord) -> None:
        """Atomically persist materialized job state."""
        j_dir = self._job_dir(job.job_id)
        j_dir.mkdir(parents=True, exist_ok=True)
        j_file = require_within_root(j_dir / "job.json", j_dir)
        write_json_atomic(j_file, job.model_dump())

    def load_job(self, job_id: str) -> JobRecord:
        """Load materialized job state."""
        j_dir = self._job_dir(job_id)
        j_file = require_within_root(j_dir / "job.json", j_dir)
        if not j_file.is_file():
            raise RigMateError(
                f"Job not found: '{job_id}'",
                code=RigMateErrorCode.JOB_NOT_FOUND,
                details={"job_id": job_id},
            )
        data = read_json(j_file)
        return JobRecord(**data)

    def job_exists(self, job_id: str) -> bool:
        """Check if job exists on disk."""
        try:
            j_dir = self._job_dir(job_id)
            return (j_dir / "job.json").is_file()
        except Exception:
            return False

    def list_jobs_and_corrupt(self) -> Tuple[List[JobRecord], List[CorruptJobRecord]]:
        """List all persisted jobs on disk, separating valid jobs from corrupted ones."""
        if not self.jobs_dir.exists():
            return [], []
        jobs: List[JobRecord] = []
        corrupt: List[CorruptJobRecord] = []
        for d in self.jobs_dir.iterdir():
            if not d.is_dir():
                continue
            job_file = d / "job.json"
            if job_file.is_file():
                try:
                    jobs.append(self.load_job(d.name))
                except Exception as exc:
                    err_code = getattr(exc, "code", RigMateErrorCode.VALIDATION_FAILED)
                    corrupt.append(
                        CorruptJobRecord(
                            job_id=d.name,
                            job_dir=str(d),
                            error_code=err_code,
                            message=str(exc),
                        )
                    )
            else:
                # Directory exists but job.json is missing
                corrupt.append(
                    CorruptJobRecord(
                        job_id=d.name,
                        job_dir=str(d),
                        error_code=RigMateErrorCode.JOB_NOT_FOUND,
                        message=f"Job directory '{d.name}' exists but has no job.json",
                    )
                )
        return jobs, corrupt

    def list_jobs(self) -> List[JobRecord]:
        """List all valid persisted jobs on disk."""
        valid, _ = self.list_jobs_and_corrupt()
        return valid

    def list_corrupt_jobs(self) -> List[CorruptJobRecord]:
        """List all corrupted job directories found on disk."""
        _, corrupt = self.list_jobs_and_corrupt()
        return corrupt

    def save_plan(self, plan: PreparedPlan) -> None:
        """Atomically persist prepared plan."""
        j_dir = self._job_dir(plan.job_id)
        j_dir.mkdir(parents=True, exist_ok=True)
        p_file = require_within_root(j_dir / "plan.json", j_dir)
        write_json_atomic(p_file, plan.model_dump())

    def load_plan(self, job_id: str) -> Optional[PreparedPlan]:
        """Load prepared plan if present."""
        j_dir = self._job_dir(job_id)
        p_file = require_within_root(j_dir / "plan.json", j_dir)
        if not p_file.is_file():
            return None
        data = read_json(p_file)
        return PreparedPlan(**data)

    def append_event(self, event: RigMateEvent) -> None:
        """Append event to events.jsonl."""
        if not event.job_id:
            raise ValueError("Event must have job_id to append to job journal")
        j_dir = self._job_dir(event.job_id)
        j_dir.mkdir(parents=True, exist_ok=True)
        ev_file = require_within_root(j_dir / "events.jsonl", j_dir)
        append_jsonl(ev_file, event.model_dump())

    def read_events(self, job_id: str, tolerate_truncated_final: bool = True) -> List[RigMateEvent]:
        """Read and parse all events from job journal."""
        j_dir = self._job_dir(job_id)
        ev_file = require_within_root(j_dir / "events.jsonl", j_dir)
        if not ev_file.is_file():
            return []
        events: List[RigMateEvent] = []
        for raw in iter_jsonl(ev_file, tolerate_truncated_final_line=tolerate_truncated_final):
            events.append(RigMateEvent(**raw))
        return events

    def save_operation(self, op: OperationEnvelope) -> None:
        """Persist operation intent."""
        validate_safe_id(op.operation_id, "operation_id")
        j_dir = self._job_dir(op.job_id)
        ops_dir = j_dir / "operations"
        ops_dir.mkdir(parents=True, exist_ok=True)
        op_file = require_within_root(ops_dir / f"{op.operation_id}.json", ops_dir)
        write_json_atomic(op_file, op.model_dump())

    def load_operation(self, job_id: str, operation_id: str) -> Optional[OperationEnvelope]:
        """Load persisted operation envelope."""
        validate_safe_id(operation_id, "operation_id")
        j_dir = self._job_dir(job_id)
        ops_dir = j_dir / "operations"
        op_file = require_within_root(ops_dir / f"{operation_id}.json", ops_dir)
        if not op_file.is_file():
            return None
        data = read_json(op_file)
        return OperationEnvelope(**data)

    def save_receipt(self, job_id: str, receipt: OperationReceipt) -> None:
        """Persist operation receipt."""
        validate_safe_id(receipt.operation_id, "operation_id")
        j_dir = self._job_dir(job_id)
        rcpt_dir = j_dir / "receipts"
        rcpt_dir.mkdir(parents=True, exist_ok=True)
        rcpt_file = require_within_root(rcpt_dir / f"{receipt.operation_id}.json", rcpt_dir)
        write_json_atomic(rcpt_file, receipt.model_dump())

    def load_receipt(self, job_id: str, operation_id: str) -> Optional[OperationReceipt]:
        """Load persisted receipt."""
        validate_safe_id(operation_id, "operation_id")
        j_dir = self._job_dir(job_id)
        rcpt_dir = j_dir / "receipts"
        rcpt_file = require_within_root(rcpt_dir / f"{operation_id}.json", rcpt_dir)
        if not rcpt_file.is_file():
            return None
        data = read_json(rcpt_file)
        return OperationReceipt(**data)

    def save_recovery_record(self, job_id: str, data: Dict[str, Union[str, int, float, bool, None, dict, list]]) -> None:
        """Persist recovery decision record."""
        j_dir = self._job_dir(job_id)
        j_dir.mkdir(parents=True, exist_ok=True)
        rec_file = require_within_root(j_dir / "recovery.json", j_dir)
        write_json_atomic(rec_file, data)

    def load_recovery_record(self, job_id: str) -> Optional[Dict[str, Union[str, int, float, bool, None, dict, list]]]:
        """Load recovery decision record."""
        j_dir = self._job_dir(job_id)
        rec_file = require_within_root(j_dir / "recovery.json", j_dir)
        if not rec_file.is_file():
            return None
        return read_json(rec_file)

