"""RigMate neutral character analysis package.

Deterministic diagnostic inspection and rule evaluation.
Pure Python standard library. Zero external dependencies.
"""

from rigmate.analysis.rig import (
    RigAnalyzer,
    FINGER_PATTERNS,
    SIDE_PATTERNS,
)

__all__ = [
    "RigAnalyzer",
    "FINGER_PATTERNS",
    "SIDE_PATTERNS",
]
