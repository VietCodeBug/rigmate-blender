"""Unit tests for startup recovery scanning, reconciliation, and journal gap detection."""

import pytest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.events import RigMateEvent
from rigmate.core.jobs import JobRecord, JobStatus
from rigmate.core.recovery import RecoveryScanner, reconcile_job_events
from rigmate.storage.job_store import JobStore


def test_reconcile_detects_sequence_gap():
    job = JobRecord(
        job_id="job_gap",
        project_id="proj_1",
        correlation_id="corr_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        last_event_sequence=0,
    )
    # Events with gap: 0, 2
    events = [
        RigMateEvent(
            event_id="e0",
            sequence=0,
            event_type="job.created",
            project_id="proj_1",
            job_id="job_gap",
        ),
        RigMateEvent(
            event_id="e2",
            sequence=2,  # Missing sequence 1!
            event_type="job.prepared",
            project_id="proj_1",
            job_id="job_gap",
        ),
    ]

    with pytest.raises(RigMateError) as exc:
        reconcile_job_events(job, events)
    assert exc.value.code == RigMateErrorCode.EVENT_SEQUENCE_INVALID


def test_recovery_scanner_classifies_prepared_job(tmp_path):
    store = JobStore(tmp_path)
    job = JobRecord(
        job_id="job_prep",
        project_id="proj_1",
        correlation_id="corr_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        status=JobStatus.PREPARED,
        last_event_sequence=0,
    )
    store.save_job(job)
    store.append_event(
        RigMateEvent(
            event_id="e0",
            sequence=0,
            event_type="job.created",
            project_id="proj_1",
            job_id="job_prep",
        )
    )

    scanner = RecoveryScanner(store)
    decisions = scanner.scan_and_reconcile()
    assert len(decisions) == 1
    assert decisions[0].recommended_action == "safe_to_resume_or_cancel"
    assert decisions[0].apply_started is False
