"""Diagnostic analysis logic for Rig and Mesh decoupled completely from Blender and Pydantic.

Canonical implementation lives in `rigmate.blender_addon.analyzer` (Blender-safe, stdlib only).
Re-exported here for backwards compatibility with core and external Python callers.
"""

from rigmate.blender_addon.analyzer import (
    RigAnalyzer,
    FINGER_PATTERNS,
    SIDE_PATTERNS,
)

__all__ = [
    "RigAnalyzer",
    "FINGER_PATTERNS",
    "SIDE_PATTERNS",
]
