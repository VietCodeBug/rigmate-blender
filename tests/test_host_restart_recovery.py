"""Comprehensive tests proving headless host control plane restart recovery and ACK-loss safety.

Scenarios tested:
- True Process-Restart ACK-Loss Proof (Core A + Host A destroyed; Core B + Host B recover, mutation_count strictly 1)
- Crash before host apply (host never executed; no blind re-apply)
- Crash after host mutation before local receipt (recovered from durable host state)
- Host status unknown (safe transition to recovery_required, no blind re-apply)
- Verification failure after mutation (transition to recovery_required, never completed)
- Non-destructive recovery restore from checkpoint
- Cancel requested during execution
"""

import pytest

from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.contracts.host import HostAdapter, HostApplyResult, HostStatusEnum
from rigmate.core.job_service import JobService
from rigmate.core.jobs import JobRecord, JobStatus
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.core.plans import PreparedPlan
from rigmate.core.receipts import OperationReceipt, ReceiptStatus
from rigmate.core.recovery import RecoveryAction, RecoveryScanner
from rigmate.testing.durable_host import DurableFakeHost


def _setup_environment(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    host_state_dir = tmp_path / "host_state"
    host_state_dir.mkdir(parents=True, exist_ok=True)

    test_model = project_root / "character.blend"
    test_model.write_text("v1_character_data", encoding="utf-8")

    return project_root, storage_root, host_state_dir, test_model


def test_fresh_object_reconstruction_ack_loss_proof(tmp_path):
    """
    MANDATORY RELEASE BLOCKER:
    1. Core A and Host A initialized.
    2. Host A mutates document (mutation_count advances 0 -> 1).
    3. Host A drops ACK (simulated network/process failure).
    4. Core A and Host A objects are COMPLETELY DESTROYED.
    5. Core B and Host B created from SAME persistent storage paths.
    6. Core B runs recovery / resume_job.
    7. Core B queries Host B for durable operation status.
    8. Host B loads status from disk; Core B MUST NOT dispatch apply again.
    9. Verification succeeds -> job COMPLETED.
    10. mutation_count remains STRICTLY 1!
    """
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    # Step 1: Create Host A and Core A
    host_a = DurableFakeHost(
        host_state_dir=host_state_dir,
        initial_revision="rev_1",
        next_revision="rev_2",
        simulate_ack_loss=True,  # Mutates, saves to disk, then drops ACK!
    )
    assert host_a.mutation_count == 0

    core_a = JobService(storage_root, project_root, host_a)

    # Step 2: Create, inspect, and prepare job
    job = core_a.create_job(
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
    )
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core_a.start_inspecting(job.job_id)
    core_a.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core_a.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_ack_restart",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_ack_restart",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Character_Hero"},
    )

    # Step 3: Core A persists operation and emits transition to APPLYING
    core_a.store.save_operation(op)
    job.current_operation_id = op.operation_id
    core_a._transition_job(
        job,
        JobStatus.APPLYING,
        "operation.apply_started",
        {"operation_id": op.operation_id, "tool": op.tool},
    )
    core_a.idempotency.register(op)

    # Core A dispatches apply to Host A.
    # Host A mutates (count becomes 1), writes to disk, and drops connection.
    # Core A process terminates immediately upon connection drop (no receipt persisted in Core!).
    with pytest.raises(ConnectionResetError):
        host_a.apply_operation(op)

    assert host_a.mutation_count == 1



    # Step 4: DESTROY CORE A AND HOST A (Zero RAM survival!)
    del core_a
    del host_a

    # Step 5: CREATE NEW INSTANCES Core B and Host B from the SAME storage directories
    host_b = DurableFakeHost(host_state_dir=host_state_dir)
    assert host_b.mutation_count == 1  # Persisted on disk!

    core_b = JobService(storage_root, project_root, host_b)

    # Step 6: Startup scan & recovery
    scanner = RecoveryScanner(core_b.store, host_b)
    decisions = scanner.scan_and_reconcile()
    assert len(decisions) >= 1

    # Step 7: Core B executes actionable resume_job()
    resumed_job = core_b.resume_job(job.job_id)

    # Step 8: Assert outcome
    assert resumed_job.status == JobStatus.COMPLETED
    assert resumed_job.terminal_reason is not None

    # Step 9: CRITICAL INVARIANT: Mutation count remains STRICTLY 1!
    assert host_b.mutation_count == 1

# Backward-compatible alias
test_true_process_restart_ack_loss_proof = test_fresh_object_reconstruction_ack_loss_proof


def test_crash_before_host_apply(tmp_path):
    """
    Core persisted intent and applying state, but crashed before calling host.
    Restart queries host -> host authoritatively returns NOT_FOUND.
    All preconditions (identity, checkpoint, lock, revision) revalidate:
    Core safely redispatches the SAME operation identity -> completes with mutation_count == 1!
    """
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host_a = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_1", next_revision="rev_2")
    core_a = JobService(storage_root, project_root, host_a)

    job = core_a.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core_a.start_inspecting(job.job_id)
    core_a.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core_a.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_crash_before",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_crash_before",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Character_Redispatched"},
    )

    # Simulate crash before host: save op and transition to applying directly in store
    core_a.store.save_operation(op)
    job.status = JobStatus.APPLYING
    job.current_operation_id = op.operation_id
    core_a.store.save_job(job)

    # Process A dies
    del core_a
    del host_a

    # Process B starts
    host_b = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_1", next_revision="rev_2")
    core_b = JobService(storage_root, project_root, host_b)

    assert host_b.mutation_count == 0

    # Host confirms NOT_FOUND authoritatively
    st = host_b.query_operation_status(op.operation_id, op.idempotency_key)
    assert st.state == HostStatusEnum.NOT_FOUND
    assert st.authoritative is True

    # Resume safely redispatches the operation
    resumed = core_b.resume_job(job.job_id)
    assert resumed.status == JobStatus.COMPLETED

    # Mutation happened exactly once during redispatch
    assert host_b.mutation_count == 1
    assert host_b.current_revision == "rev_2"


def test_crash_before_host_apply_stale_revision_halts_redispatch(tmp_path):
    """If host revision advanced before NOT_FOUND redispatch, halt with TARGET_STALE."""
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host_a = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_1")
    core_a = JobService(storage_root, project_root, host_a)

    job = core_a.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core_a.start_inspecting(job.job_id)
    core_a.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core_a.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_stale_redispatch",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_stale_redispatch",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Character_Redispatched"},
    )

    core_a.store.save_operation(op)
    job.status = JobStatus.APPLYING
    job.current_operation_id = op.operation_id
    core_a.store.save_job(job)

    del core_a
    del host_a

    # Host B has advanced to rev_2 (concurrent change)
    host_b = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_2")
    core_b = JobService(storage_root, project_root, host_b)

    resumed = core_b.resume_job(job.job_id)
    assert resumed.status == JobStatus.RECOVERY_REQUIRED
    assert resumed.error.code == RigMateErrorCode.TARGET_STALE
    assert host_b.mutation_count == 0


def test_crash_before_host_apply_unknown_status_halts_redispatch(tmp_path):
    """If host query returns UNKNOWN, NEVER re-apply; transition to recovery_required."""
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host_a = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_1")
    core_a = JobService(storage_root, project_root, host_a)

    job = core_a.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core_a.start_inspecting(job.job_id)
    core_a.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core_a.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_unknown_redispatch",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_unknown_redispatch",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Character_Redispatched"},
    )

    core_a.store.save_operation(op)
    job.status = JobStatus.APPLYING
    job.current_operation_id = op.operation_id
    core_a.store.save_job(job)

    del core_a
    del host_a

    # Host B simulated in UNKNOWN state
    host_b = DurableFakeHost(host_state_dir=host_state_dir, simulate_host_unknown=True)
    core_b = JobService(storage_root, project_root, host_b)

    resumed = core_b.resume_job(job.job_id)
    assert resumed.status == JobStatus.RECOVERY_REQUIRED
    assert resumed.error.code == RigMateErrorCode.RESULT_UNVERIFIED
    assert host_b.mutation_count == 0


def test_crash_before_host_apply_unavailable_status_halts_redispatch(tmp_path):
    """If host query returns UNAVAILABLE, NEVER re-apply; transition to recovery_required."""
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host_a = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_1")
    core_a = JobService(storage_root, project_root, host_a)

    job = core_a.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core_a.start_inspecting(job.job_id)
    core_a.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core_a.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_unavail_redispatch",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_unavail_redispatch",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Character_Redispatched"},
    )

    core_a.store.save_operation(op)
    job.status = JobStatus.APPLYING
    job.current_operation_id = op.operation_id
    core_a.store.save_job(job)

    del core_a
    del host_a

    # Host B simulated as UNAVAILABLE
    host_b = DurableFakeHost(host_state_dir=host_state_dir, simulate_host_unavailable=True)
    core_b = JobService(storage_root, project_root, host_b)

    resumed = core_b.resume_job(job.job_id)
    assert resumed.status == JobStatus.RECOVERY_REQUIRED
    assert resumed.error.code == RigMateErrorCode.RESULT_UNVERIFIED
    assert host_b.mutation_count == 0


def test_crash_after_host_mutation_before_local_receipt(tmp_path):
    """
    Host mutation occurred and is durably persisted in host state.
    Core crashed before persisting local receipt.
    Restart queries host, discovers execution, verifies outcome, transitions to COMPLETED.
    """
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host_a = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_1", next_revision="rev_2")
    core_a = JobService(storage_root, project_root, host_a)

    job = core_a.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core_a.start_inspecting(job.job_id)
    core_a.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core_a.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_crash_after",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_crash_after",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Hero_After"},
    )

    core_a.store.save_operation(op)
    job.status = JobStatus.APPLYING
    job.current_operation_id = op.operation_id
    core_a.store.save_job(job)

    # Host executes mutation directly (e.g. received call)
    host_a.apply_operation(op)
    assert host_a.mutation_count == 1

    # Core crashes BEFORE saving receipt locally!
    del core_a
    del host_a

    # Process B starts
    host_b = DurableFakeHost(host_state_dir=host_state_dir)
    core_b = JobService(storage_root, project_root, host_b)

    # Resume discovers host executed mutation
    resumed = core_b.resume_job(job.job_id)
    assert resumed.status == JobStatus.COMPLETED
    assert host_b.mutation_count == 1


def test_unknown_host_status_transitions_to_recovery_required(tmp_path):
    """
    Host is unavailable or cannot confirm status after uncertain apply.
    Must transition to recovery_required, NEVER blindly re-apply.
    """
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    # Host simulates host unavailable
    host = DurableFakeHost(host_state_dir=host_state_dir, simulate_host_unavailable=True)
    core = JobService(storage_root, project_root, host)

    job = core.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core.start_inspecting(job.job_id)
    core.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_unknown_host",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_unknown_host",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    core.store.save_operation(op)
    job.status = JobStatus.APPLYING
    job.current_operation_id = op.operation_id
    core.store.save_job(job)

    # Resume when host status cannot be confirmed
    resumed = core.resume_job(job.job_id)
    assert resumed.status == JobStatus.RECOVERY_REQUIRED
    assert resumed.error.code == RigMateErrorCode.RESULT_UNVERIFIED


def test_verification_failure_prevents_completion(tmp_path):
    """
    Host executes mutation, but verification fails.
    Must transition to recovery_required; NEVER completed.
    """
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host = DurableFakeHost(
        host_state_dir=host_state_dir,
        initial_revision="rev_1",
        next_revision="rev_2",
        simulate_verify_failure=True,  # Host mutates, but verify fails!
    )
    core = JobService(storage_root, project_root, host)

    job = core.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core.start_inspecting(job.job_id)
    core.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_verify_fail",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_verify_fail",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    result_job = core.start_apply(job.job_id, op)
    assert result_job.status == JobStatus.RECOVERY_REQUIRED
    assert result_job.error.code == RigMateErrorCode.RESULT_UNVERIFIED

    # Checkpoint remains intact
    assert result_job.checkpoint_ref is not None


def test_non_destructive_recovery_restore(tmp_path):
    """Non-destructive recovery restores preserved checkpoint files to copy."""
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host = DurableFakeHost(host_state_dir=host_state_dir, simulate_verify_failure=True)
    core = JobService(storage_root, project_root, host)

    job = core.create_job("proj_1", "host_1", "doc_1", "rev_1")
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    core.start_inspecting(job.job_id)
    core.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    job = core.get_job(job.job_id)

    op = OperationEnvelope(
        operation_id="op_recover_test",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_recover_test",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    core.start_apply(job.job_id, op)
    job = core.get_job(job.job_id)
    assert job.status == JobStatus.RECOVERY_REQUIRED

    # Execute recovery restore
    recovered_job = core.recover_job(job.job_id)
    assert recovered_job.status == JobStatus.RECOVERED

    # Assert source file was NOT destroyed or overwritten
    assert test_model.is_file()
    assert test_model.read_text(encoding="utf-8") == "v1_character_data"


def test_cancel_requested_during_execution(tmp_path):
    """Cancelling during mutation marks cancel_requested and does not falsely claim cancelled."""
    project_root, storage_root, host_state_dir, test_model = _setup_environment(tmp_path)

    host = DurableFakeHost(host_state_dir=host_state_dir)
    core = JobService(storage_root, project_root, host)

    job = core.create_job("proj_1", "host_1", "doc_1", "rev_1")
    job.status = JobStatus.APPLYING
    core.store.save_job(job)

    cancelled = core.request_cancel(job.job_id, reason="User clicked stop during mutation")
    assert cancelled.status == JobStatus.CANCEL_REQUESTED
    assert cancelled.cancel_requested is True
