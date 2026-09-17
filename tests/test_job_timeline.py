"""Unit tests for timeline building and formatting."""

import pytest
from rigmate.core.events import RigMateEvent
from rigmate.core.timeline import build_job_timeline, format_timeline_text
from rigmate.storage.job_store import JobStore


def test_job_timeline_generation(tmp_path):
    store = JobStore(tmp_path)
    job_id = "job_time_1"

    store.append_event(
        RigMateEvent(
            event_id="e0",
            sequence=0,
            event_type="job.created",
            project_id="proj_1",
            job_id=job_id,
            timestamp="2026-09-17T10:00:00Z",
            payload={"job_type": "mutation"},
        )
    )
    store.append_event(
        RigMateEvent(
            event_id="e1",
            sequence=1,
            event_type="job.prepared",
            project_id="proj_1",
            job_id=job_id,
            timestamp="2026-09-17T10:00:02Z",
            payload={"from_status": "inspecting", "to_status": "prepared"},
        )
    )

    timeline = build_job_timeline(job_id, store)
    assert len(timeline) == 2
    assert timeline[0].sequence == 0
    assert timeline[1].sequence == 1

    text = format_timeline_text(timeline)
    assert "000 2026-09-17T10:00:00Z [job.created]" in text
    assert "001 2026-09-17T10:00:02Z [job.prepared] (inspecting -> prepared)" in text
