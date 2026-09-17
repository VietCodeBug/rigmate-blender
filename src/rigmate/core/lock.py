"""Document and project mutation lock mechanism.

Ensures single-writer mutation protection per document/project.
Lock contains:
- lock_id
- project_id
- host_instance_id
- document_id
- job_id
- pid
- created_at
- updated_at

Detects stale locks via PID liveness checks and timeout thresholds.
"""

import os
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, Field
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.ids import _gen_prefixed_uuid
from rigmate.core.time_utils import to_utc_iso, parse_utc_iso, utc_now
from rigmate.storage.json_io import read_json, write_json_atomic


class LockMetadata(BaseModel):
    lock_id: str
    project_id: str
    host_instance_id: str
    document_id: str
    job_id: str
    pid: int
    created_at: str = Field(default_factory=to_utc_iso)
    updated_at: str = Field(default_factory=to_utc_iso)


def _is_pid_alive(pid: int) -> bool:
    """Check if process with given PID is still running on the system."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class DocumentLock:
    """
    Filesystem-backed lock for a document/project writer critical section.
    """

    def __init__(
        self,
        lock_dir: Union[str, Path],
        project_id: str,
        host_instance_id: str,
        document_id: str,
        stale_timeout_seconds: int = 300,
    ):
        self.lock_dir = Path(lock_dir)
        self.project_id = project_id
        self.host_instance_id = host_instance_id
        self.document_id = document_id
        self.stale_timeout_seconds = stale_timeout_seconds

        # Safe lock filename
        safe_doc = "".join(c if c.isalnum() or c in "-_" else "_" for c in document_id)
        self.lock_file = self.lock_dir / f"{project_id}_{safe_doc}.lock"

    def acquire(self, job_id: str) -> LockMetadata:
        """
        Acquire lock for job_id.
        Raises RigMateError(LOCK_CONFLICT) if lock is actively held.
        """
        self.lock_dir.mkdir(parents=True, exist_ok=True)

        if self.lock_file.exists():
            try:
                data = read_json(self.lock_file)
                existing = LockMetadata(**data)

                # Check if held by the exact same job
                if existing.job_id == job_id:
                    existing.updated_at = to_utc_iso()
                    write_json_atomic(self.lock_file, existing.model_dump())
                    return existing

                # Check if stale (dead PID or expired)
                pid_alive = _is_pid_alive(existing.pid)
                lock_age = (utc_now() - parse_utc_iso(existing.updated_at)).total_seconds()

                if not pid_alive or lock_age > self.stale_timeout_seconds:
                    # Safe to reclaim stale lock
                    pass
                else:
                    raise RigMateError(
                        f"Document '{self.document_id}' is locked by job '{existing.job_id}' (PID {existing.pid})",
                        code=RigMateErrorCode.LOCK_CONFLICT,
                        details={
                            "lock_file": str(self.lock_file),
                            "existing_job_id": existing.job_id,
                            "pid": existing.pid,
                            "updated_at": existing.updated_at,
                        },
                    )
            except RigMateError:
                raise
            except Exception:
                # Corrupted lock file: allow replacement
                pass

        meta = LockMetadata(
            lock_id=_gen_prefixed_uuid("lock"),
            project_id=self.project_id,
            host_instance_id=self.host_instance_id,
            document_id=self.document_id,
            job_id=job_id,
            pid=os.getpid(),
        )
        write_json_atomic(self.lock_file, meta.model_dump())
        return meta

    def release(self, job_id: str) -> bool:
        """Release lock if held by job_id."""
        if not self.lock_file.exists():
            return False

        try:
            data = read_json(self.lock_file)
            existing = LockMetadata(**data)
            if existing.job_id == job_id:
                self.lock_file.unlink(missing_ok=True)
                return True
        except Exception:
            self.lock_file.unlink(missing_ok=True)
            return True
        return False
