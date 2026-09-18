"""Diagnostic analysis logic for Rig and Mesh decoupled completely from Blender and Pydantic.

Canonical implementation lives in `rigmate.analysis.rig` (pure standard library).
Re-exported here for backwards compatibility with core and external Python callers.
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
