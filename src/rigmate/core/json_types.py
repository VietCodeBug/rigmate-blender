"""Lightweight JSON compatibility validation.

Verifies that payloads, event attributes, and receipt facts conform strictly
to valid JSON types without non-standard types (NaN, Infinity, bytes, raw objects).
"""

import math
from typing import Any


class JsonCompatibilityError(TypeError):
    """Raised when an object cannot be cleanly encoded to JSON."""
    pass


def is_json_compatible(val: Any) -> bool:
    """Check if value is composed strictly of valid standard JSON types."""
    try:
        assert_json_compatible(val)
        return True
    except (JsonCompatibilityError, TypeError, ValueError):
        return False


def assert_json_compatible(val: Any, path: str = "$") -> None:
    """
    Recursively check that val contains only:
    - None (null)
    - bool
    - int or finite float (rejects NaN, Infinity)
    - str
    - list or tuple of JSON-compatible values
    - dict with string keys and JSON-compatible values

    Raises JsonCompatibilityError on incompatible types.
    """
    if val is None or isinstance(val, (bool, str)):
        return

    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            raise JsonCompatibilityError(f"At {path}: Non-finite float '{val}' is not valid JSON")
        return

    if isinstance(val, (list, tuple)):
        for idx, item in enumerate(val):
            assert_json_compatible(item, f"{path}[{idx}]")
        return

    if isinstance(val, dict):
        for k, v in val.items():
            if not isinstance(k, str):
                raise JsonCompatibilityError(f"At {path}: Dictionary key '{k}' must be a string, got {type(k).__name__}")
            assert_json_compatible(v, f"{path}['{k}']")
        return

    # Incompatible type
    raise JsonCompatibilityError(
        f"At {path}: Type '{type(val).__name__}' is not JSON-compatible (value: {val!r})"
    )
