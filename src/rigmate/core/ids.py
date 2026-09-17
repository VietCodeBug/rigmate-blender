"""Canonical identifier generation helpers.

Produces collision-safe, UUID-based, filesystem-safe IDs with stable recognizable prefixes.
No timestamp-only IDs or mutable global counters.
"""

import re
import uuid

SAFE_ID_REGEX = re.compile(r"^[a-z0-9]+_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _gen_prefixed_uuid(prefix: str) -> str:
    """Generate a prefixed UUID4 string (e.g. job_550e8400-e29b-41d4-a716-446655440000)."""
    return f"{prefix}_{uuid.uuid4()}"


def new_project_id() -> str:
    """Generate a unique project ID."""
    return _gen_prefixed_uuid("proj")


def new_job_id() -> str:
    """Generate a unique job ID."""
    return _gen_prefixed_uuid("job")


def new_operation_id() -> str:
    """Generate a unique operation ID."""
    return _gen_prefixed_uuid("op")


def new_session_id() -> str:
    """Generate a unique session ID."""
    return _gen_prefixed_uuid("sess")


def new_host_instance_id() -> str:
    """Generate a unique host instance ID."""
    return _gen_prefixed_uuid("host")


def new_event_id() -> str:
    """Generate a unique event ID."""
    return _gen_prefixed_uuid("evt")


def new_correlation_id() -> str:
    """Generate a unique correlation ID for tracking request flows."""
    return _gen_prefixed_uuid("corr")


def new_checkpoint_id() -> str:
    """Generate a unique checkpoint ID."""
    return _gen_prefixed_uuid("cp")


def is_valid_id(id_str: str) -> bool:
    """Check if string matches standard prefixed-uuid format."""
    return bool(SAFE_ID_REGEX.match(id_str))
