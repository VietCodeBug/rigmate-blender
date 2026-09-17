"""Unit tests for operation idempotency tracking and conflict detection."""

import pytest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.storage.idempotency import IdempotencyRegistry, compute_operation_request_hash


def test_idempotency_same_key_same_hash(tmp_path):
    reg = IdempotencyRegistry(tmp_path)

    op1 = OperationEnvelope(
        operation_id="op_1",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.align",
        mode=OperationMode.INSPECT,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_key_1",
        arguments={"threshold": 0.05},
    )

    # Unseen key returns None
    assert reg.check(op1) is None

    # Register
    reg.register(op1)

    # Check same key with same payload
    checked = reg.check(op1)
    assert checked is not None
    assert checked.operation_id == "op_1"


def test_idempotency_conflict_detection(tmp_path):
    reg = IdempotencyRegistry(tmp_path)

    op1 = OperationEnvelope(
        operation_id="op_1",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.align",
        mode=OperationMode.INSPECT,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_key_1",
        arguments={"threshold": 0.05},
    )
    reg.register(op1)

    # Different arguments with same idempotency key
    op2 = OperationEnvelope(
        operation_id="op_2",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.align",
        mode=OperationMode.INSPECT,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_key_1",
        arguments={"threshold": 0.99},  # Changed!
    )

    with pytest.raises(RigMateError) as exc:
        reg.check(op2)
    assert exc.value.code == RigMateErrorCode.IDEMPOTENCY_CONFLICT
