"""Unit tests for JobRecord and canonical state transitions."""

import pytest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.jobs import (
    ALLOWED_TRANSITIONS,
    JobRecord,
    JobStatus,
    JobType,
    is_terminal_status,
    validate_transition,
)
from rigmate.core.receipts import ReceiptError


def test_job_transitions_valid():
    # Queued -> Inspecting -> Prepared -> Applying -> Verifying -> Completed
    validate_transition(JobStatus.QUEUED, JobStatus.INSPECTING)
    validate_transition(JobStatus.INSPECTING, JobStatus.PREPARED)
    validate_transition(JobStatus.PREPARED, JobStatus.APPLYING)
    validate_transition(JobStatus.APPLYING, JobStatus.VERIFYING)
    validate_transition(JobStatus.VERIFYING, JobStatus.COMPLETED)


def test_job_transitions_invalid():
    # Illegal transitions
    with pytest.raises(RigMateError) as exc:
        validate_transition(JobStatus.QUEUED, JobStatus.APPLYING)
    assert exc.value.code == RigMateErrorCode.INVALID_JOB_TRANSITION

    with pytest.raises(RigMateError) as exc:
        validate_transition(JobStatus.PREPARED, JobStatus.COMPLETED)
    assert exc.value.code == RigMateErrorCode.INVALID_JOB_TRANSITION


def test_job_transitions_terminal_cannot_transition():
    terminals = [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.RECOVERED]
    for term in terminals:
        assert is_terminal_status(term)
        for target in JobStatus:
            with pytest.raises(RigMateError) as exc:
                validate_transition(term, target)
            assert exc.value.code == RigMateErrorCode.INVALID_JOB_TRANSITION


def test_job_record_validation():
    job = JobRecord(
        job_id="job_123",
        project_id="proj_abc",
        correlation_id="corr_xyz",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
    )
    assert job.status == JobStatus.QUEUED
    assert job.job_type == JobType.MUTATION

    # Empty required ID rejects
    with pytest.raises(ValueError):
        JobRecord(
            job_id="",
            project_id="proj_abc",
            correlation_id="corr_xyz",
            host_instance_id="host_1",
            document_id="doc_1",
            expected_revision="rev_1",
        )

    # Completed job cannot have unresolved error
    with pytest.raises(ValueError):
        JobRecord(
            job_id="job_123",
            project_id="proj_abc",
            correlation_id="corr_xyz",
            host_instance_id="host_1",
            document_id="doc_1",
            expected_revision="rev_1",
            status=JobStatus.COMPLETED,
            error=ReceiptError(code="ERR", message="Failed"),
        )
