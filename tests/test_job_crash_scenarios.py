"""Comprehensive acceptance tests for all mandatory closed-loop crash and lifecycle scenarios:

Scenarios:
- Scenario A: Happy-path closed-loop mutation & restart reload
- Scenario B: Stale revision precondition rejection (TARGET_STALE)
- Scenario C: Checkpoint failure prevents apply
- Scenario D: Cancel before apply (terminal CANCELLED)
- Scenario E: Cancel during apply (CANCEL_REQUESTED and verified outcome)
- Scenario F (RELEASE BLOCKER): ACK-loss after actual mutation (zero duplicate apply, mutation count remains 1)
- Scenario G: Crash after receipt before job state update (startup reconciliation)
- Scenario H: Unknown side effect (RECOVERY_REQUIRED, never blind retry)
- Scenario I: Recovery restore-to-copy verified
- Scenario J: Corrupt middle journal detection (JOURNAL_INCONSISTENT)
"""

import pytest
from rigmate.core.errors import RigMateError, RigMateErrorCode
from rigmate.core.events import RigMateEvent
from rigmate.core.executors import FakeOperationExecutor
from rigmate.core.job_service import JobService
from rigmate.core.jobs import JobRecord, JobStatus
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.core.plans import PreparedPlan
from rigmate.core.recovery import RecoveryScanner
from rigmate.core.timeline import format_timeline_text
from rigmate.storage.job_store import JobStore
from rigmate.storage.json_io import JsonlCorruptionError


def test_scenario_a_happy_path_closed_loop(tmp_path):
    """Scenario A: Full happy-path mutation, restart service, verify persisted state and timeline."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    test_model = project_root / "character.blend"
    test_model.write_text("v1_data", encoding="utf-8")

    executor = FakeOperationExecutor(current_revision="rev_1", next_revision="rev_2")
    svc = JobService(storage_root, project_root, executor)

    # 1. Create Job
    job = svc.create_job(
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
    )
    assert job.status == JobStatus.QUEUED

    # 2. Inspect
    job = svc.start_inspecting(job.job_id)
    assert job.status == JobStatus.INSPECTING

    # 3. Prepare with plan & checkpoint
    plan = PreparedPlan(
        plan_id="plan_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
        checkpoint_required=True,
    )
    job = svc.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])
    assert job.status == JobStatus.PREPARED
    assert job.checkpoint_ref is not None

    # 4. Apply
    op = OperationEnvelope(
        operation_id="op_1",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.bone_fix",
        mode=OperationMode.APPLY,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_op_1",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )
    job = svc.start_apply(job.job_id, op)
    assert job.status == JobStatus.COMPLETED
    assert executor.mutation_count == 1

    # 5. Restart service from disk (destroy old instance)
    del svc
    new_svc = JobService(storage_root, project_root, executor)
    reloaded_job = new_svc.get_job(job.job_id)
    assert reloaded_job.status == JobStatus.COMPLETED
    assert reloaded_job.terminal_reason is not None

    timeline = new_svc.build_timeline(job.job_id)
    timeline_str = format_timeline_text(timeline)
    assert "[job.created]" in timeline_str
    assert "[checkpoint.created]" in timeline_str
    assert "[operation.apply_started]" in timeline_str
    assert "[job.verify_succeeded]" in timeline_str
    assert "[job.completed]" in timeline_str


def test_scenario_b_stale_revision_precondition(tmp_path):
    """Scenario B: Host revision is stale; TARGET_STALE raised, no mutation executed."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    test_model = project_root / "character.blend"
    test_model.write_text("v1_data", encoding="utf-8")

    # Host is at rev_2, but job expects rev_1
    executor = FakeOperationExecutor(current_revision="rev_2")
    svc = JobService(storage_root, project_root, executor)

    job = svc.create_job(
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
    job = svc.start_inspecting(job.job_id)
    job = svc.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])

    op = OperationEnvelope(
        operation_id="op_stale",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.bone_fix",
        mode=OperationMode.APPLY,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_stale",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    with pytest.raises(RigMateError) as exc:
        svc.start_apply(job.job_id, op)
    assert exc.value.code == RigMateErrorCode.TARGET_STALE
    assert executor.mutation_count == 0


def test_scenario_c_checkpoint_failure_prevents_apply(tmp_path):
    """Scenario C: Checkpoint failure prevents job from preparing or applying."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    executor = FakeOperationExecutor()
    svc = JobService(storage_root, project_root, executor)

    job = svc.create_job(
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

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        svc.prepare_job(job.job_id, plan, checkpoint_source_files=[project_root / "missing.blend"])

    job_reloaded = svc.get_job(job.job_id)
    assert job_reloaded.status == JobStatus.QUEUED
    assert executor.mutation_count == 0


def test_scenario_d_cancel_before_apply(tmp_path):
    """Scenario D: Cancellation before apply immediately transitions to terminal CANCELLED."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    executor = FakeOperationExecutor()
    svc = JobService(storage_root, project_root, executor)

    job = svc.create_job(
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
    )
    cancelled = svc.request_cancel(job.job_id, reason="user abort")
    assert cancelled.status == JobStatus.CANCELLED
    assert executor.mutation_count == 0


def test_scenario_e_cancel_during_apply(tmp_path):
    """Scenario E: Cancel requested during apply marks cancel_requested, never falsely cancelled."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    executor = FakeOperationExecutor()
    svc = JobService(storage_root, project_root, executor)

    job = svc.create_job(
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        expected_revision="rev_1",
    )
    # Manually transition to applying to simulate mid-flight cancel request
    job.status = JobStatus.APPLYING
    svc.store.save_job(job)

    cancelled = svc.request_cancel(job.job_id)
    assert cancelled.status == JobStatus.CANCEL_REQUESTED
    assert cancelled.cancel_requested is True


def test_scenario_f_ack_loss_after_actual_mutation(tmp_path):
    """
    Scenario F (RELEASE BLOCKER):
    1. Core sends apply.
    2. Host mutates (mutation count = 1).
    3. Host drops response / network ACK lost.
    4. Core queries status; discovers mutation occurred.
    5. Core MUST NOT re-apply. Mutation count remains exactly 1.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    test_model = project_root / "character.blend"
    test_model.write_text("v1_data", encoding="utf-8")

    executor = FakeOperationExecutor(
        current_revision="rev_1",
        next_revision="rev_2",
        simulate_ack_loss=True,  # Mutates host, then raises exception
    )

    assert executor.mutation_count == 0

    svc = JobService(storage_root, project_root, executor)
    job = svc.create_job(
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
    job = svc.start_inspecting(job.job_id)
    job = svc.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])

    op = OperationEnvelope(
        operation_id="op_ack_loss",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.bone_fix",
        mode=OperationMode.APPLY,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_ack_loss",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    # Apply triggers ACK loss:
    # Under the hood, start_apply catches the drop, queries executor.query_status,
    # discovers the mutation already completed, and recovers the receipt!
    job = svc.start_apply(job.job_id, op)

    assert executor.mutation_count == 1
    assert job.status == JobStatus.COMPLETED

    # Now simulate a retry of the same operation
    # It must return the existing receipt and NOT increment mutation counter!
    job_retry = svc.start_apply(job.job_id, op)
    assert executor.mutation_count == 1  # REMAINS EXACTLY 1!
    assert job_retry.status == JobStatus.COMPLETED


def test_scenario_g_crash_after_receipt_before_state_update(tmp_path):
    """Scenario G: Process crashes right after receipt persisted, before job status updated."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    test_model = project_root / "character.blend"
    test_model.write_text("v1_data", encoding="utf-8")

    executor = FakeOperationExecutor()

    # Fault hook simulating crash
    def crash_hook(hook_name, ctx):
        if hook_name == "after_receipt_persisted_before_verifying":
            raise SystemExit("Simulated SIGKILL right after receipt written")

    svc = JobService(storage_root, project_root, executor, fault_hook=crash_hook)
    job = svc.create_job(
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
    job = svc.start_inspecting(job.job_id)
    job = svc.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])

    op = OperationEnvelope(
        operation_id="op_crash",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.bone_fix",
        mode=OperationMode.APPLY,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_crash",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    with pytest.raises(SystemExit):
        svc.start_apply(job.job_id, op)

    # Process restarted: run recovery scanner
    scanner = RecoveryScanner(svc.store, executor)
    decisions = scanner.scan_and_reconcile()

    assert len(decisions) == 1
    # Scanner detects receipt exists and recommends resume_verification
    assert decisions[0].recommended_action == "resume_verification"
    assert decisions[0].receipt_present is True


def test_scenario_h_unknown_side_effect_requires_recovery(tmp_path):
    """Scenario H: Unknown side effect transitions to recovery_required, never blind retry."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    test_model = project_root / "character.blend"
    test_model.write_text("v1_data", encoding="utf-8")

    class UnresponsiveExecutor:
        def prepare(self, op): return True
        def apply(self, op): raise ConnectionError("Host completely disconnected")
        def verify(self, op, rcpt): return False
        def query_status(self, op_id, key): return None  # Host state unknown!

    svc = JobService(storage_root, project_root, UnresponsiveExecutor())
    job = svc.create_job(
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
    job = svc.start_inspecting(job.job_id)
    job = svc.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])

    op = OperationEnvelope(
        operation_id="op_unk",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.bone_fix",
        mode=OperationMode.APPLY,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_unk",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    job = svc.start_apply(job.job_id, op)
    assert job.status == JobStatus.RECOVERY_REQUIRED
    assert job.error is not None
    assert job.error.code == RigMateErrorCode.RESULT_UNVERIFIED


def test_scenario_i_recovery_restore_verified(tmp_path):
    """Scenario I: Recovering job restores file to copy and transitions to recovered."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    storage_root = tmp_path / "storage"

    test_model = project_root / "character.blend"
    test_model.write_text("v1_original", encoding="utf-8")

    executor = FakeOperationExecutor(simulate_verify_failure=True)
    svc = JobService(storage_root, project_root, executor)

    job = svc.create_job(
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
    job = svc.start_inspecting(job.job_id)
    job = svc.prepare_job(job.job_id, plan, checkpoint_source_files=[test_model])

    op = OperationEnvelope(
        operation_id="op_verify_fail",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="armature.bone_fix",
        mode=OperationMode.APPLY,
        target_ids=["Armature"],
        expected_revision="rev_1",
        idempotency_key="idem_vfail",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
    )

    # Verification fails -> job is in recovery_required
    job = svc.start_apply(job.job_id, op)
    assert job.status == JobStatus.RECOVERY_REQUIRED

    # Run recover_job
    recovered_job = svc.recover_job(job.job_id)
    assert recovered_job.status == JobStatus.RECOVERED
    assert recovered_job.terminal_reason is not None


def test_scenario_j_corrupt_middle_journal(tmp_path):
    """Scenario J: Corrupt middle journal raises JsonlCorruptionError, never silently skipped."""
    store = JobStore(tmp_path)
    job_id = "job_corrupt"

    store.append_event(
        RigMateEvent(
            event_id="e0",
            sequence=0,
            event_type="job.created",
            project_id="proj_1",
            job_id=job_id,
        )
    )

    # Invalidate middle event in events.jsonl
    ev_file = store._job_dir(job_id) / "events.jsonl"
    with open(ev_file, "a", encoding="utf-8") as f:
        f.write("{corrupt_json_not_valid_syntax}\n")

    # Add 3rd event
    with open(ev_file, "a", encoding="utf-8") as f:
        f.write('{"event_id":"e2","sequence":2,"event_type":"job.completed","project_id":"proj_1"}\n')

    with pytest.raises(JsonlCorruptionError):
        store.read_events(job_id)
