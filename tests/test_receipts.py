"""Unit tests for OperationReceipt domain model."""

from pathlib import Path
import pytest
from pydantic import ValidationError
from rigmate.core.receipts import OperationReceipt, ReceiptStatus, ReceiptError


def test_receipt_valid_completed():
    receipt = OperationReceipt(
        operation_id="op_100",
        status=ReceiptStatus.COMPLETED,
        host_revision_before="rev_0",
        host_revision_after="rev_1",
        verified_at="2026-09-17T08:00:00Z",
        facts={"vertices_after": 48000},
    )
    assert receipt.status == ReceiptStatus.COMPLETED
    assert receipt.host_revision_after == "rev_1"


def test_receipt_valid_recovered():
    recovered = OperationReceipt(
        operation_id="op_100",
        status=ReceiptStatus.RECOVERED,
        host_revision_before="rev_0",
        host_revision_after="rev_0",
        verified_at="2026-09-17T08:05:00Z",
        facts={"recovered_from_checkpoint": "cp_001"},
    )
    assert recovered.status == ReceiptStatus.RECOVERED


def test_receipt_valid_failed_and_recovery_required():
    failed = OperationReceipt(
        operation_id="op_100",
        status=ReceiptStatus.FAILED,
        host_revision_before="rev_0",
        error=ReceiptError(code="OUT_OF_SCOPE_PATH", message="Path was outside workspace"),
    )
    assert failed.status == ReceiptStatus.FAILED
    assert failed.error.code == "OUT_OF_SCOPE_PATH"

    recovery_req = OperationReceipt(
        operation_id="op_100",
        status=ReceiptStatus.RECOVERY_REQUIRED,
        host_revision_before="rev_0",
        error=ReceiptError(code="RESULT_UNVERIFIED", message="Could not confirm host revision"),
    )
    assert recovery_req.status == ReceiptStatus.RECOVERY_REQUIRED


def test_receipt_host_revision_before_required():
    # Missing / None host_revision_before
    with pytest.raises(ValidationError):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before=None,  # type: ignore
            host_revision_after="rev_1",
            verified_at="2026-09-17T08:00:00Z",
        )

    # Empty string host_revision_before
    with pytest.raises(ValidationError, match="host_revision_before.*must be a non-empty string"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="   ",
            host_revision_after="rev_1",
            verified_at="2026-09-17T08:00:00Z",
        )


def test_receipt_schema_version_enforced():
    with pytest.raises(ValidationError):
        OperationReceipt(
            schema_version="2.0.0",  # type: ignore
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after="rev_1",
            verified_at="2026-09-17T08:00:00Z",
        )


def test_receipt_operation_id_required():
    with pytest.raises(ValidationError, match="operation_id.*must be a non-empty string"):
        OperationReceipt(
            operation_id="",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after="rev_1",
            verified_at="2026-09-17T08:00:00Z",
        )


def test_receipt_completed_without_verification_rejected():
    with pytest.raises(ValidationError, match="requires a valid 'verified_at' timestamp"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after="rev_1",
            verified_at=None,
        )

    with pytest.raises(ValidationError, match="requires 'host_revision_after'"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after=None,
            verified_at="2026-09-17T08:00:00Z",
        )


def test_receipt_completed_with_error_rejected():
    with pytest.raises(ValidationError, match="cannot have an unresolved 'error'"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after="rev_1",
            verified_at="2026-09-17T08:00:00Z",
            error=ReceiptError(code="SOME_ERROR", message="An error occurred"),
        )


def test_receipt_failed_requires_structured_error():
    with pytest.raises(ValidationError, match="requires a structured 'error' object"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.FAILED,
            host_revision_before="rev_0",
            error=None,
        )


def test_receipt_error_structure_enforced():
    # Error code cannot be empty
    with pytest.raises(ValidationError, match="ReceiptError 'code' must be a non-empty string"):
        ReceiptError(code="", message="Failed")

    # Error message cannot be empty
    with pytest.raises(ValidationError, match="ReceiptError 'message' must be a non-empty string"):
        ReceiptError(code="ERR", message="")


def test_receipt_facts_and_changes_json_compatibility():
    with pytest.raises(ValidationError, match="Receipt payload validation failed"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after="rev_1",
            verified_at="2026-09-17T08:00:00Z",
            facts={"invalid_val": Path("/not/json")},
        )
