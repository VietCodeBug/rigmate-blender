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


SAFE_SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


def validate_safe_id(id_str: str, field_name: str = "id") -> str:
    """
    Validate that an identifier is safe for use in filesystem paths.
    Rejects directory traversal (..), slashes (/ or \\), colons, and special characters.
    Raises RigMateError(ARTIFACT_PATH_INVALID) if unsafe.
    """
    from rigmate.core.errors import RigMateError, RigMateErrorCode

    if not isinstance(id_str, str):
        raise RigMateError(
            f"Field '{field_name}' must be a string",
            code=RigMateErrorCode.ARTIFACT_PATH_INVALID,
            details={"field": field_name, "value": str(id_str)},
        )

    clean = id_str.strip()
    if not clean:
        raise RigMateError(
            f"Field '{field_name}' cannot be empty",
            code=RigMateErrorCode.ARTIFACT_PATH_INVALID,
            details={"field": field_name},
        )

    if ".." in clean or "/" in clean or "\\" in clean or "\0" in clean or ":" in clean:
        raise RigMateError(
            f"Field '{field_name}' contains illegal path characters: '{id_str}'",
            code=RigMateErrorCode.ARTIFACT_PATH_INVALID,
            details={"field": field_name, "value": id_str},
        )

    if not SAFE_SLUG_REGEX.match(clean):
        raise RigMateError(
            f"Field '{field_name}' contains invalid characters (must be alphanumeric, underscore, hyphen): '{id_str}'",
            code=RigMateErrorCode.ARTIFACT_PATH_INVALID,
            details={"field": field_name, "value": id_str},
        )

    return clean
