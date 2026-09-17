"""Unit tests for semantic schema versioning and compatibility."""

import pytest
from rigmate.core.schema_version import (
    parse_schema_version,
    check_schema_compatibility,
    SchemaCompatibility,
    SchemaVersion,
)


def test_schema_version_parsing():
    v1 = parse_schema_version("1.0")
    assert v1 == SchemaVersion(1, 0, 0)
    assert str(v1) == "1.0.0"

    v2 = parse_schema_version("2.3.4")
    assert v2 == SchemaVersion(2, 3, 4)

    with pytest.raises(ValueError, match="Malformed schema version string"):
        parse_schema_version("v1.0")

    with pytest.raises(ValueError, match="Malformed schema version string"):
        parse_schema_version("alpha.1")


def test_schema_compatibility_rules():
    # 1. Exact match -> SUPPORTED
    assert check_schema_compatibility("1.0.0", "1.0.0") == SchemaCompatibility.SUPPORTED
    assert check_schema_compatibility("1.2.3", "1.2.3") == SchemaCompatibility.SUPPORTED

    # 2. Older minor/patch in same major -> SUPPORTED
    assert check_schema_compatibility("1.0.0", "1.2.0") == SchemaCompatibility.SUPPORTED
    assert check_schema_compatibility("1.1.2", "1.1.5") == SchemaCompatibility.SUPPORTED

    # 3. Newer minor in same major -> READ_ONLY
    assert check_schema_compatibility("1.3.0", "1.2.0") == SchemaCompatibility.READ_ONLY
    assert check_schema_compatibility("1.2.1", "1.2.0") == SchemaCompatibility.READ_ONLY

    # 4. Different major version -> UNSUPPORTED
    assert check_schema_compatibility("2.0.0", "1.0.0") == SchemaCompatibility.UNSUPPORTED
    assert check_schema_compatibility("0.9.0", "1.0.0") == SchemaCompatibility.UNSUPPORTED
