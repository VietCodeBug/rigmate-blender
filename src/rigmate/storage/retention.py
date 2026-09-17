"""Pure retention policy calculation for checkpoints and local snapshots.

Calculates which checkpoints are candidates for cleanup without deleting any files.
Preserves:
- Pinned checkpoints (user-protected)
- Checkpoints required by active jobs
- Newest pre-mutation checkpoint if marked protected
- Configurable maximum checkpoint count and byte budget
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CheckpointMetadata(BaseModel):
    """Metadata describing a stored checkpoint snapshot."""
    checkpoint_id: str
    created_at: str  # ISO-8601 string
    size_bytes: int = 0
    is_pinned: bool = False
    is_required_by_active_job: bool = False
    is_newest_pre_mutation: bool = False


class RetentionPolicy(BaseModel):
    """Configuration constraints for checkpoint retention."""
    max_checkpoints: int = 20
    max_total_bytes: int = 500 * 1024 * 1024  # 500 MB default budget


class RetentionDecision(BaseModel):
    """Calculated decision of which checkpoints to retain and which to clean up."""
    retained_ids: List[str]
    candidates_for_deletion: List[str]
    total_retained_bytes: int
    freed_bytes: int


def calculate_retention(
    checkpoints: List[CheckpointMetadata],
    policy: RetentionPolicy,
) -> RetentionDecision:
    """
    Pure calculation: evaluates a list of checkpoints against retention policy rules.
    Returns which checkpoint IDs are candidates for cleanup.
    Does NOT delete any files.
    """
    # Sort chronological newest first
    sorted_cps = sorted(checkpoints, key=lambda c: c.created_at, reverse=True)

    retained: List[CheckpointMetadata] = []
    candidates_for_deletion: List[str] = []

    # 1. Immediately retain protected items: pinned, required by active job, or newest pre-mutation
    for cp in sorted_cps:
        if cp.is_pinned or cp.is_required_by_active_job or cp.is_newest_pre_mutation:
            retained.append(cp)

    # 2. Iterate non-protected candidates and evaluate max_checkpoints & max_total_bytes
    protected_ids = {cp.checkpoint_id for cp in retained}
    
    current_bytes = sum(cp.size_bytes for cp in retained)

    for cp in sorted_cps:
        if cp.checkpoint_id in protected_ids:
            continue

        # Check count constraint (total retained would exceed max_checkpoints)
        if len(retained) >= policy.max_checkpoints:
            candidates_for_deletion.append(cp.checkpoint_id)
            continue

        # Check byte budget constraint
        if current_bytes + cp.size_bytes > policy.max_total_bytes:
            candidates_for_deletion.append(cp.checkpoint_id)
            continue

        # Safe to retain
        retained.append(cp)
        current_bytes += cp.size_bytes

    total_retained_bytes = sum(cp.size_bytes for cp in retained)
    freed_bytes = sum(
        cp.size_bytes for cp in checkpoints if cp.checkpoint_id in candidates_for_deletion
    )

    return RetentionDecision(
        retained_ids=[cp.checkpoint_id for cp in retained],
        candidates_for_deletion=candidates_for_deletion,
        total_retained_bytes=total_retained_bytes,
        freed_bytes=freed_bytes,
    )
