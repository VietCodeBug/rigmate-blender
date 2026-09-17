"""Unit tests for canonical ID generation helpers."""

from rigmate.core.ids import (
    new_project_id,
    new_job_id,
    new_operation_id,
    new_session_id,
    new_host_instance_id,
    new_event_id,
    new_correlation_id,
    new_checkpoint_id,
    is_valid_id,
)


def test_ids_prefixes_and_format():
    assert new_project_id().startswith("proj_")
    assert new_job_id().startswith("job_")
    assert new_operation_id().startswith("op_")
    assert new_session_id().startswith("sess_")
    assert new_host_instance_id().startswith("host_")
    assert new_event_id().startswith("evt_")
    assert new_correlation_id().startswith("corr_")
    assert new_checkpoint_id().startswith("cp_")


def test_ids_validity_and_uniqueness():
    generated = [new_job_id() for _ in range(500)]
    assert len(set(generated)) == 500
    for jid in generated:
        assert is_valid_id(jid) is True

    assert is_valid_id("invalid-id-format") is False
    assert is_valid_id("job_123") is False
