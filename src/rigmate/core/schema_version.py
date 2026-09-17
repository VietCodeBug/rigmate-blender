"""Semantic schema versioning and compatibility helpers.

Evaluates schema compatibility without heavy external SemVer dependencies.
Policy:
- Same major version + equal or lower minor version -> SUPPORTED
- Same major version + higher minor version -> READ_ONLY
- Different major version -> UNSUPPORTED
"""

import re
from enum import Enum
from typing import NamedTuple, Union


class SchemaCompatibility(str, Enum):
    """Compatibility classification for a document schema version."""
    SUPPORTED = "supported"        # Fully supported for read/write
    READ_ONLY = "read_only"        # Newer minor schema in same major, safe for read-only
    UNSUPPORTED = "unsupported"    # Different major schema or invalid version


class SchemaVersion(NamedTuple):
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


SEMVER_REGEX = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")


def parse_schema_version(version_str: str) -> SchemaVersion:
    """
    Parse a version string like '1.0' or '1.2.3' into a SchemaVersion.
    Raises ValueError on malformed format.
    """
    if not isinstance(version_str, str):
        raise ValueError(f"Version must be a string, got {type(version_str).__name__}")

    match = SEMVER_REGEX.match(version_str.strip())
    if not match:
        raise ValueError(f"Malformed schema version string: '{version_str}' (expected 'X.Y' or 'X.Y.Z')")

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3)) if match.group(3) is not None else 0
    return SchemaVersion(major=major, minor=minor, patch=patch)


def check_schema_compatibility(
    incoming_version: Union[str, SchemaVersion],
    supported_version: Union[str, SchemaVersion],
) -> SchemaCompatibility:
    """
    Evaluate compatibility of an incoming schema version against our supported version.

    Rules:
    1. Different major version -> UNSUPPORTED (breaking changes)
    2. Same major version and incoming <= supported -> SUPPORTED
    3. Same major version and incoming > supported -> READ_ONLY (newer minor feature additions)
    """
    inc = parse_schema_version(incoming_version) if isinstance(incoming_version, str) else incoming_version
    sup = parse_schema_version(supported_version) if isinstance(supported_version, str) else supported_version

    if inc.major != sup.major:
        return SchemaCompatibility.UNSUPPORTED

    if (inc.minor < sup.minor) or (inc.minor == sup.minor and inc.patch <= sup.patch):
        return SchemaCompatibility.SUPPORTED

    return SchemaCompatibility.READ_ONLY
