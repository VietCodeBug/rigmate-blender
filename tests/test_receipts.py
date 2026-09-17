"""Unit tests for OperationReceipt domain model."""

import pytest
from pydantic import ValidationError
from rigmate.core.receipts import OperationReceipt, ReceiptStatus


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


def test_receipt_completed_without_verification_rejected():
    with pytest.raises(ValidationError, match="requires a valid 'verified_at' timestamp"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after="rev_1",
            verified_at=None,
        )


def test_receipt_completed_with_error_rejected():
    with pytest.raises(ValidationError, match="cannot have an unresolved 'error'"):
        OperationReceipt(
            operation_id="op_100",
            status=ReceiptStatus.COMPLETED,
            host_revision_before="rev_0",
            host_revision_after="rev_1",
            verified_at="2026-09-17T08:00:00Z",
            error={"code": "SOME_ERROR"},
        )


def test_receipt_valid_failed_and_recovery():
    failed = OperationReceipt(
        operation_id="op_100",
        status=ReceiptStatus.FAILED,
        error={"code": "OUT_OF_SCOPE_PATH", "message": "Path was outside workspace"},
    )
    assert failed.status == ReceiptStatus.FAILED

    recovery_req = OperationReceipt(
        operation_id="op_100",
        status=ReceiptStatus.RECOVERY_REQUIRED,
        error={"code": "RESULT_UNVERIFIED", "message": "Could not confirm host revision"},
    )
    assert recovery_req.status == ReceiptStatus.RECOVERY_REQUIRED
