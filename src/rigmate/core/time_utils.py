"""Canonical UTC timestamp helpers.

Enforces timezone-aware UTC datetime instances and standard ISO 8601 string representations.
Rejects naive datetimes to avoid accidental local timezone persistence bugs.
"""

from datetime import datetime, timezone
from typing import Optional, Union


def utc_now() -> datetime:
    """Return current timezone-aware datetime in UTC."""
    return datetime.now(timezone.utc)


def to_utc_iso(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as canonical ISO 8601 UTC string (ending with 'Z').
    If dt is None, formats utc_now().
    Rejects naive datetimes.
    Converts aware non-UTC datetimes to UTC.
    """
    if dt is None:
        target = utc_now()
    else:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise ValueError(f"Naive datetime rejected: '{dt}'. Must be timezone-aware.")
        target = dt.astimezone(timezone.utc)

    # Format ISO 8601 with trailing 'Z'
    iso = target.isoformat()
    if iso.endswith("+00:00"):
        return iso[:-6] + "Z"
    return iso


Optional_dt = Union[datetime, None]


def parse_utc_iso(iso_str: str) -> datetime:
    """
    Parse an ISO 8601 string into a timezone-aware UTC datetime.
    Rejects invalid formats or naive strings.
    """
    if not isinstance(iso_str, str):
        raise ValueError(f"Expected ISO string, got {type(iso_str).__name__}")

    clean_str = iso_str.strip()
    if clean_str.endswith("Z"):
        clean_str = clean_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(clean_str)
    except Exception as e:
        raise ValueError(f"Malformed ISO timestamp string '{iso_str}': {e}")

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Parsed datetime lacks timezone offset: '{iso_str}'")

    return dt.astimezone(timezone.utc)
