"""Compatibility shim for Blender add-on RigAnalyzer.

Canonical implementation now lives in `rigmate.analysis.rig` (pure Python standard library).
Re-exported here for backwards compatibility within the Blender add-on package.
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
