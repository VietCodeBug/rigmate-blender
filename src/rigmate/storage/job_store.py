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

from pathlib import Path
from typing import Dict, List, Optional, Union
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.events import RigMateEvent
from rigmate.core.jobs import JobRecord
from rigmate.core.operations import OperationEnvelope
from rigmate.core.plans import PreparedPlan
from rigmate.core.receipts import OperationReceipt
from rigmate.storage.json_io import (
    append_jsonl,
    iter_jsonl,
    read_json,
    write_json_atomic,
)


class JobStore:
    """
    Filesystem repository managing persisted job state, plans, journals, operations, and receipts.
    """

    def __init__(self, storage_root: Union[str, Path]):
        self.storage_root = Path(storage_root).resolve()
        self.jobs_dir = self.storage_root / "jobs"

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def save_job(self, job: JobRecord) -> None:
        """Atomically persist materialized job state."""
        j_dir = self._job_dir(job.job_id)
        j_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(j_dir / "job.json", job.model_dump())

    def load_job(self, job_id: str) -> JobRecord:
        """Load materialized job state."""
        j_file = self._job_dir(job_id) / "job.json"
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
        return (self._job_dir(job_id) / "job.json").is_file()

    def list_jobs(self) -> List[JobRecord]:
        """List all persisted jobs on disk."""
        if not self.jobs_dir.exists():
            return []
        jobs: List[JobRecord] = []
        for d in self.jobs_dir.iterdir():
            if (d / "job.json").is_file():
                try:
                    jobs.append(self.load_job(d.name))
                except Exception:
                    continue
        return jobs

    def save_plan(self, plan: PreparedPlan) -> None:
        """Atomically persist prepared plan."""
        j_dir = self._job_dir(plan.job_id)
        j_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(j_dir / "plan.json", plan.model_dump())

    def load_plan(self, job_id: str) -> Optional[PreparedPlan]:
        """Load prepared plan if present."""
        p_file = self._job_dir(job_id) / "plan.json"
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
        append_jsonl(j_dir / "events.jsonl", event.model_dump())

    def read_events(self, job_id: str, tolerate_truncated_final: bool = True) -> List[RigMateEvent]:
        """Read and parse all events from job journal."""
        ev_file = self._job_dir(job_id) / "events.jsonl"
        if not ev_file.is_file():
            return []
        events: List[RigMateEvent] = []
        for raw in iter_jsonl(ev_file, tolerate_truncated_final_line=tolerate_truncated_final):
            events.append(RigMateEvent(**raw))
        return events

    def save_operation(self, op: OperationEnvelope) -> None:
        """Persist operation intent."""
        ops_dir = self._job_dir(op.job_id) / "operations"
        ops_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(ops_dir / f"{op.operation_id}.json", op.model_dump())

    def load_operation(self, job_id: str, operation_id: str) -> Optional[OperationEnvelope]:
        """Load persisted operation envelope."""
        op_file = self._job_dir(job_id) / "operations" / f"{operation_id}.json"
        if not op_file.is_file():
            return None
        data = read_json(op_file)
        return OperationEnvelope(**data)

    def save_receipt(self, job_id: str, receipt: OperationReceipt) -> None:
        """Persist operation receipt."""
        rcpt_dir = self._job_dir(job_id) / "receipts"
        rcpt_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(rcpt_dir / f"{receipt.operation_id}.json", receipt.model_dump())

    def load_receipt(self, job_id: str, operation_id: str) -> Optional[OperationReceipt]:
        """Load persisted receipt."""
        rcpt_file = self._job_dir(job_id) / "receipts" / f"{operation_id}.json"
        if not rcpt_file.is_file():
            return None
        data = read_json(rcpt_file)
        return OperationReceipt(**data)

    def save_recovery_record(self, job_id: str, data: Dict[str, Union[str, int, float, bool, None, dict, list]]) -> None:
        """Persist recovery decision record."""
        j_dir = self._job_dir(job_id)
        j_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(j_dir / "recovery.json", data)

    def load_recovery_record(self, job_id: str) -> Optional[Dict[str, Union[str, int, float, bool, None, dict, list]]]:
        """Load recovery decision record."""
        rec_file = self._job_dir(job_id) / "recovery.json"
        if not rec_file.is_file():
            return None
        return read_json(rec_file)
