"""Unit tests for job cancellation semantics."""

import pytest
from rigmate.core.executors import FakeOperationExecutor
from rigmate.core.job_service import JobService
from rigmate.core.jobs import JobStatus


def test_cancel_before_apply(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    executor = FakeOperationExecutor()
    svc = JobService(storage_root, project_root, executor)

    job = svc.create_job(
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
    )
    assert job.status == JobStatus.QUEUED

    # Cancel while queued
    cancelled = svc.request_cancel(job.job_id, reason="user clicked stop")
    assert cancelled.status == JobStatus.CANCELLED

    # Idempotent cancel on cancelled job
    recancelled = svc.request_cancel(job.job_id)
    assert recancelled.status == JobStatus.CANCELLED
