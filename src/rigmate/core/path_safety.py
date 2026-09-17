"""Pure-Python path containment and safety utilities.

Prevents directory traversal, unauthorized access outside configured project roots,
and rejects escaping relative/symlink paths.
"""

from pathlib import Path
from typing import Union


class PathSafetyError(ValueError):
    """Base exception for path containment violations."""
    code = "path_safety.violation"


class PathTraversalError(PathSafetyError):
    """Raised when a path traverses outside the authorized root."""
    code = "path_safety.traversal_detected"


class PathOutsideRootError(PathSafetyError):
    """Raised when a path is strictly outside the authorized root."""
    code = "path_safety.outside_root"


def canonicalize_path(path: Union[str, Path]) -> Path:
    """
    Resolve path to an absolute, normalized form without resolving symlinks
    away from non-existent targets, or use resolve() for existing targets.
    """
    p = Path(path)
    try:
        return p.resolve()
    except Exception:
        # Fallback if resolve fails on some platform quirks
        return p.absolute()


def is_within_root(target: Union[str, Path], root: Union[str, Path]) -> bool:
    """
    Check if the target path resides strictly inside or matches the root directory.
    Rejects directory traversal (..), sibling paths, and root escapes.
    """
    try:
        resolved_root = canonicalize_path(root)
        resolved_target = canonicalize_path(target)
        
        # In Python 3.9+, is_relative_to is standard on Path
        return resolved_target.is_relative_to(resolved_root)
    except Exception:
        return False


def require_within_root(target: Union[str, Path], root: Union[str, Path]) -> Path:
    """
    Enforce that target is inside root. Returns the canonical Path.
    Raises PathTraversalError or PathOutsideRootError if outside.
    """
    resolved_root = canonicalize_path(root)
    resolved_target = canonicalize_path(target)

    if not resolved_target.is_relative_to(resolved_root):
        raise PathOutsideRootError(
            f"Path '{resolved_target}' escapes authorized root '{resolved_root}'"
        )
    return resolved_target


def safe_relative_path(target: Union[str, Path], root: Union[str, Path]) -> Path:
    """
    Compute relative path from root to target, ensuring target is within root.
    Returns relative Path. Raises PathOutsideRootError if target is outside root.
    """
    canonical_target = require_within_root(target, root)
    canonical_root = canonicalize_path(root)
    return canonical_target.relative_to(canonical_root)
