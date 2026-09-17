"""Unit tests for centralized structured error model."""

import json
from rigmate.core.errors import RigMateError, RigMateErrorCode


def test_errors_basic_structure():
    err = RigMateError(
        message="Host process is offline or unreachable",
        code=RigMateErrorCode.HOST_UNAVAILABLE,
        details={"host": "127.0.0.1", "port": 8765},
    )

    assert err.code == "HOST_UNAVAILABLE"
    assert err.message == "Host process is offline or unreachable"
    assert err.details["port"] == 8765

    # Check string representation
    err_str = str(err)
    assert "[HOST_UNAVAILABLE]" in err_str
    assert "8765" in err_str


def test_errors_serialization_and_causality():
    cause_exc = ConnectionRefusedError("Connection refused by target machine")
    err = RigMateError(
        message="Checkpoint storage failed",
        code=RigMateErrorCode.CHECKPOINT_FAILED,
        details={"checkpoint_id": "cp_123"},
        cause=cause_exc,
    )

    d = err.to_dict()
    assert d["code"] == "CHECKPOINT_FAILED"
    assert d["details"]["checkpoint_id"] == "cp_123"
    assert "ConnectionRefusedError" in d["cause"]

    # Must be JSON-serializable
    dumped = json.dumps(d)
    assert "CHECKPOINT_FAILED" in dumped
