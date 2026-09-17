"""Unit tests for generic event envelope."""

import pytest
from pydantic import ValidationError
from rigmate.core.events import RigMateEvent


def test_events_valid_envelope():
    evt = RigMateEvent(
        event_id="evt_12345",
        sequence=0,
        event_type="checkpoint.created",
        project_id="proj_hero",
        payload={"checkpoint_id": "cp_001", "size_bytes": 1024},
    )

    assert evt.sequence == 0
    assert evt.timestamp.endswith("Z")
    assert evt.payload["size_bytes"] == 1024

    # Round-trip JSON validation
    dumped = evt.model_dump_json()
    loaded = RigMateEvent.model_validate_json(dumped)
    assert loaded.event_id == "evt_12345"
    assert loaded.sequence == 0


def test_events_negative_sequence_rejected():
    with pytest.raises(ValidationError):
        RigMateEvent(
            event_id="evt_123",
            sequence=-1,
            event_type="test",
            project_id="proj_1",
        )


def test_events_invalid_timestamp_rejected():
    with pytest.raises(ValidationError):
        RigMateEvent(
            event_id="evt_123",
            sequence=1,
            timestamp="not_a_utc_timestamp",
            event_type="test",
            project_id="proj_1",
        )
