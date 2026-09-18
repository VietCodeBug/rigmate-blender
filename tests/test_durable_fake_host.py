"""Tests for DurableFakeHost filesystem persistence, idempotency, revision control, and safe mutation."""

import pytest

from rigmate.contracts.host import HostStatusEnum
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.testing.durable_host import DurableFakeHost


def test_host_persistence_across_recreation(tmp_path):
    """Host state and operation status must survive destruction of Python objects."""
    state_dir = tmp_path / "host_state"

    # Host A mutates document
    host_a = DurableFakeHost(state_dir, initial_revision="rev_1", next_revision="rev_2")
    assert host_a.mutation_count == 0

    op = OperationEnvelope(
        operation_id="op_durable_1",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        prepared_plan_ref="plan_1",
        checkpoint_ref="cp_1",
        idempotency_key="idem_durable_1",
        arguments={"new_name": "Hero"},
    )

    res_a = host_a.apply_operation(op)
    assert res_a.host_revision_after == "rev_2"
    assert host_a.mutation_count == 1

    # Destroy Host A
    del host_a

    # Create Host B pointing to the exact same storage directory
    host_b = DurableFakeHost(state_dir)
    assert host_b.mutation_count == 1

    # Host B can query durable operation status
    recovered = host_b.query_operation_status("op_durable_1", "idem_durable_1")
    assert recovered is not None
    assert recovered.state == HostStatusEnum.EXECUTED
    assert recovered.apply_result is not None
    assert recovered.apply_result.operation_id == "op_durable_1"
    assert recovered.apply_result.host_revision_after == "rev_2"
    assert recovered.apply_result.execution_state == "applied"
    assert recovered.authoritative is True


def test_stale_revision_rejection(tmp_path):
    """Host must reject operations expecting an older revision without mutating."""
    state_dir = tmp_path / "host_state"
    host = DurableFakeHost(state_dir, initial_revision="rev_2")

    op_stale = OperationEnvelope(
        operation_id="op_stale",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",  # Host is at rev_2!
        prepared_plan_ref="plan_1",
        checkpoint_ref="cp_1",
        idempotency_key="idem_stale",

    )

    with pytest.raises(RigMateError) as exc:
        host.prepare_operation(op_stale)
    assert exc.value.code == RigMateErrorCode.TARGET_STALE

    with pytest.raises(RigMateError) as exc:
        host.apply_operation(op_stale)
    assert exc.value.code == RigMateErrorCode.TARGET_STALE

    assert host.mutation_count == 0


def test_host_idempotency_exact_replay(tmp_path):
    """Replaying exact duplicate request returns cached result with zero additional mutations."""
    state_dir = tmp_path / "host_state"
    host = DurableFakeHost(state_dir, initial_revision="rev_1", next_revision="rev_2")

    op = OperationEnvelope(
        operation_id="op_replay",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        prepared_plan_ref="plan_1",
        checkpoint_ref="cp_1",
        idempotency_key="idem_replay",
        arguments={"new_name": "Character_V2"},
    )

    res1 = host.apply_operation(op)
    assert host.mutation_count == 1

    # Exact replay
    res2 = host.apply_operation(op)
    assert host.mutation_count == 1  # Still exactly 1!
    assert res2.host_revision_after == res1.host_revision_after
    assert res2.operation_id == res1.operation_id


def test_host_idempotency_conflict(tmp_path):
    """Using same idempotency key with conflicting request payload must raise IDEMPOTENCY_CONFLICT."""
    state_dir = tmp_path / "host_state"
    host = DurableFakeHost(state_dir, initial_revision="rev_1", next_revision="rev_2")

    op1 = OperationEnvelope(
        operation_id="op_orig",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        prepared_plan_ref="plan_1",
        checkpoint_ref="cp_1",
        idempotency_key="idem_conflict_test",
        arguments={"new_name": "Character_A"},
    )
    host.apply_operation(op1)

    op2 = OperationEnvelope(
        operation_id="op_conflicting",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        prepared_plan_ref="plan_1",
        checkpoint_ref="cp_1",
        idempotency_key="idem_conflict_test",  # Same key
        arguments={"new_name": "Character_B"},  # Changed arguments!
    )

    with pytest.raises(RigMateError) as exc:
        host.apply_operation(op2)
    assert exc.value.code == RigMateErrorCode.IDEMPOTENCY_CONFLICT


def test_safe_mutation_object_rename(tmp_path):
    """Deterministic object.rename updates durable fake document state."""
    state_dir = tmp_path / "host_state"
    host = DurableFakeHost(state_dir, initial_revision="rev_1", next_revision="rev_2")

    doc_before = host.get_or_create_document("doc_1")
    assert "Character" in doc_before["objects"]

    op = OperationEnvelope(
        operation_id="op_rename",
        job_id="job_1",
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        prepared_plan_ref="plan_1",
        checkpoint_ref="cp_1",
        idempotency_key="idem_rename",
        arguments={"new_name": "Player_Hero"},
    )

    res = host.apply_operation(op)
    assert res.execution_state == "applied"

    doc_after = host.get_or_create_document("doc_1")
    assert "Character" not in doc_after["objects"]
    assert "Player_Hero" in doc_after["objects"]
    assert doc_after["current_revision"] == "rev_2"


def test_query_operation_status_states(tmp_path):
    """Verify explicit HostOperationStatus distinctions: NOT_FOUND, UNKNOWN, UNAVAILABLE."""
    state_dir = tmp_path / "host_state"

    # 1. NOT_FOUND: reachable host with empty registry returns authoritative NOT_FOUND
    host = DurableFakeHost(state_dir)
    st_not_found = host.query_operation_status("op_unseen", "idem_unseen")
    assert st_not_found.state == HostStatusEnum.NOT_FOUND
    assert st_not_found.authoritative is True
    assert st_not_found.apply_result is None

    # 2. UNAVAILABLE: simulated transport drop
    host_unavail = DurableFakeHost(state_dir, simulate_host_unavailable=True)
    st_unavail = host_unavail.query_operation_status("op_any", "idem_any")
    assert st_unavail.state == HostStatusEnum.UNAVAILABLE
    assert st_unavail.authoritative is False

    # 3. UNKNOWN: ambiguous host state
    host_unknown = DurableFakeHost(state_dir, simulate_host_unknown=True)
    st_unknown = host_unknown.query_operation_status("op_any", "idem_any")
    assert st_unknown.state == HostStatusEnum.UNKNOWN
    assert st_unknown.authoritative is False
