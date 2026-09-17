"""Unit tests for JSON compatibility validation."""

import math
from pathlib import Path
import pytest
from rigmate.core.json_types import (
    is_json_compatible,
    assert_json_compatible,
    JsonCompatibilityError,
)


def test_json_types_valid_data():
    valid = {
        "str": "hello",
        "int": 42,
        "float": 3.14159,
        "bool": True,
        "null": None,
        "list": [1, "two", False, None, {"nested": [3, 4]}],
    }
    assert is_json_compatible(valid) is True
    assert_json_compatible(valid)


def test_json_types_nan_and_inf_rejected():
    with pytest.raises(JsonCompatibilityError, match="Non-finite float"):
        assert_json_compatible({"val": float("nan")})

    with pytest.raises(JsonCompatibilityError, match="Non-finite float"):
        assert_json_compatible({"val": float("inf")})


def test_json_types_raw_objects_rejected():
    # Raw Path rejected
    with pytest.raises(JsonCompatibilityError, match="not JSON-compatible"):
        assert_json_compatible({"path": Path("/root/dir")})

    # Non-string key rejected
    with pytest.raises(JsonCompatibilityError, match="must be a string"):
        assert_json_compatible({123: "value"})

    # Raw bytes rejected
    with pytest.raises(JsonCompatibilityError, match="not JSON-compatible"):
        assert_json_compatible({"raw": b"binary_data"})
