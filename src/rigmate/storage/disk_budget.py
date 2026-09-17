"""Preflight disk budget calculation utilities.

Evaluates whether sufficient disk space exists before launching operations or generating checkpoints.
Does not delete or modify any files.
"""

import shutil
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel


class DiskBudgetResult(BaseModel):
    allowed: bool
    required_total: int
    available: int
    shortfall: int
    safety_margin: int


def calculate_disk_budget(
    required_bytes: int,
    available_bytes: int,
    safety_margin_bytes: int = 100 * 1024 * 1024,  # 100 MB default safety margin
    estimated_checkpoint_bytes: int = 0,
) -> DiskBudgetResult:
    """
    Pure calculation: evaluates if available_bytes can accommodate required_bytes,
    safety_margin_bytes, and optional estimated_checkpoint_bytes.

    Rejects negative values.
    """
    if required_bytes < 0 or available_bytes < 0 or safety_margin_bytes < 0 or estimated_checkpoint_bytes < 0:
        raise ValueError("Disk budget byte values must be non-negative")

    required_total = required_bytes + safety_margin_bytes + estimated_checkpoint_bytes
    shortfall = max(0, required_total - available_bytes)
    allowed = (available_bytes >= required_total)

    return DiskBudgetResult(
        allowed=allowed,
        required_total=required_total,
        available=available_bytes,
        shortfall=shortfall,
        safety_margin=safety_margin_bytes,
    )


def check_path_disk_budget(
    path: Union[str, Path],
    required_bytes: int,
    safety_margin_bytes: int = 100 * 1024 * 1024,
    estimated_checkpoint_bytes: int = 0,
) -> DiskBudgetResult:
    """Inspect actual filesystem free space and calculate budget for a path."""
    p = Path(path).resolve()
    target_dir = p if p.is_dir() else p.parent
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    usage = shutil.disk_usage(str(target_dir))
    return calculate_disk_budget(
        required_bytes=required_bytes,
        available_bytes=usage.free,
        safety_margin_bytes=safety_margin_bytes,
        estimated_checkpoint_bytes=estimated_checkpoint_bytes,
    )
