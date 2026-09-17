"""Unit tests for JobStore persistence, journal append, and event sequence ordering."""

import pytest
from rigmate.core.events import RigMateEvent
from rigmate.core.jobs import JobRecord, JobStatus
from rigmate.storage.job_store import JobStore


def test_job_store_save_load_list(tmp_path):
    store = JobStore(tmp_path)
    job = JobRecord(
        job_id="job_test_1",
        project_id="proj_1",
        correlation_id="corr_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
    )

    store.save_job(job)
    assert store.job_exists("job_test_1")

    loaded = store.load_job("job_test_1")
    assert loaded.job_id == "job_test_1"
    assert loaded.status == JobStatus.QUEUED

    all_jobs = store.list_jobs()
    assert len(all_jobs) == 1
    assert all_jobs[0].job_id == "job_test_1"


def test_job_store_journal_append_and_read(tmp_path):
    store = JobStore(tmp_path)
    ev1 = RigMateEvent(
        event_id="evt_1",
        sequence=0,
        event_type="job.created",
        project_id="proj_1",
        job_id="job_test_1",
        correlation_id="corr_1",
    )
    ev2 = RigMateEvent(
        event_id="evt_2",
        sequence=1,
        event_type="job.inspect_started",
        project_id="proj_1",
        job_id="job_test_1",
        correlation_id="corr_1",
    )

    store.append_event(ev1)
    store.append_event(ev2)

    events = store.read_events("job_test_1")
    assert len(events) == 2
    assert events[0].sequence == 0
    assert events[1].sequence == 1
    assert events[0].event_type == "job.created"
    assert events[1].event_type == "job.inspect_started"
