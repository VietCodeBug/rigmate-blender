"""Generic event envelope for job journals, event streams, and UI synchronization.

Contains metadata, monotonic sequence number, canonical UTC timestamp,
and arbitrary JSON-compatible payload.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from rigmate.core.time_utils import to_utc_iso, parse_utc_iso


class RigMateEvent(BaseModel):
    """
    Standard event envelope.
    - sequence: Non-negative monotonic sequence index (>= 0)
    - timestamp: Canonical ISO 8601 UTC timestamp
    - payload: Arbitrary JSON-serializable dictionary
    """
    schema_version: str = "1.0.0"
    event_id: str
    sequence: int = Field(ge=0)
    timestamp: str = Field(default_factory=to_utc_iso)
    event_type: str
    project_id: str
    job_id: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def validate_utc_timestamp(cls, v: str) -> str:
        # Ensures timestamp is valid parseable UTC ISO string
        parse_utc_iso(v)
        return v

    @field_validator("event_id", "event_type", "project_id")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Field cannot be empty")
        return clean
