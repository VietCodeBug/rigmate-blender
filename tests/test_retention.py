"""Unit tests for checkpoint retention calculation logic."""

from rigmate.storage.retention import (
    CheckpointMetadata,
    RetentionPolicy,
    calculate_retention,
)


def test_retention_preserves_pinned_and_active_job():
    checkpoints = [
        CheckpointMetadata(checkpoint_id="cp_1", created_at="2026-09-17T10:00:00Z", size_bytes=100, is_pinned=True),
        CheckpointMetadata(checkpoint_id="cp_2", created_at="2026-09-17T11:00:00Z", size_bytes=100, is_required_by_active_job=True),
        CheckpointMetadata(checkpoint_id="cp_3", created_at="2026-09-17T12:00:00Z", size_bytes=100),
        CheckpointMetadata(checkpoint_id="cp_4", created_at="2026-09-17T13:00:00Z", size_bytes=100),
    ]

    # Policy allows max 2 checkpoints
    policy = RetentionPolicy(max_checkpoints=2, max_total_bytes=1000)
    decision = calculate_retention(checkpoints, policy)

    # cp_1 (pinned) and cp_2 (active job) must always be retained
    assert "cp_1" in decision.retained_ids
    assert "cp_2" in decision.retained_ids

    # cp_3 and cp_4 were evaluated against the count limit
    assert "cp_3" in decision.candidates_for_deletion


def test_retention_enforces_byte_budget():
    checkpoints = [
        CheckpointMetadata(checkpoint_id="cp_newest", created_at="2026-09-17T14:00:00Z", size_bytes=60),
        CheckpointMetadata(checkpoint_id="cp_middle", created_at="2026-09-17T12:00:00Z", size_bytes=50),
        CheckpointMetadata(checkpoint_id="cp_oldest", created_at="2026-09-17T10:00:00Z", size_bytes=50),
    ]

    # Budget is 100 bytes. Newest takes 60. Middle takes 50 (sum=110 > 100) -> candidates for deletion
    policy = RetentionPolicy(max_checkpoints=10, max_total_bytes=100)
    decision = calculate_retention(checkpoints, policy)

    assert "cp_newest" in decision.retained_ids
    assert "cp_middle" in decision.candidates_for_deletion
    assert "cp_oldest" in decision.candidates_for_deletion
    assert decision.freed_bytes == 100
