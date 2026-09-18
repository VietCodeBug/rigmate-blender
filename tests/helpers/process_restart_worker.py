"""Standalone worker process executed via subprocess to prove real OS process restart recovery.

Each phase runs in a fresh, isolated Python interpreter.
Zero in-memory state or module caching survives between phases.
"""

import json
import os
import sys
from pathlib import Path

from rigmate.core.host_protocol import HostStatusEnum, host_request_from_operation
from rigmate.core.job_service import JobService
from rigmate.core.jobs import JobStatus
from rigmate.core.operations import OperationEnvelope, OperationMode
from rigmate.core.plans import PreparedPlan
from rigmate.testing.durable_host import DurableFakeHost


def run_phase_a_ack_loss(storage_root: Path, project_root: Path, host_state_dir: Path, meta_file: Path) -> None:
    """Phase A: Mutate on host, drop ACK, abnormal process termination."""
    pid = os.getpid()

    test_model = project_root / "character.blend"
    test_model.write_text("v1_data", encoding="utf-8")

    host_a = DurableFakeHost(
        host_state_dir=host_state_dir,
        initial_revision="rev_1",
        next_revision="rev_2",
        simulate_ack_loss=True,
    )
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
        operation_id="op_subprocess_ack",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_subprocess_ack",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Character_Subprocess"},
    )

    core_a.store.save_operation(op)
    job.current_operation_id = op.operation_id
    core_a._transition_job(
        job,
        JobStatus.APPLYING,
        "operation.apply_started",
        {"operation_id": op.operation_id, "tool": op.tool},
    )
    core_a.idempotency.register(op)

    # Dispatch to host (host mutates to 1 and raises ConnectionResetError)
    try:
        host_op = host_request_from_operation(op)
        host_a.apply_operation(host_op)
    except ConnectionResetError:
        pass

    # Save Phase A forensic output
    meta = {
        "phase_a_pid": pid,
        "job_id": job.job_id,
        "operation_id": op.operation_id,
        "mutation_count": host_a.mutation_count,
        "current_revision": host_a.current_revision,
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    # Immediate abnormal process termination: simulates abrupt crash before receipt persistence!
    os._exit(42)


def run_phase_b_ack_loss(storage_root: Path, project_root: Path, host_state_dir: Path, meta_file: Path, out_file: Path) -> None:
    """Phase B: Fresh Python interpreter recovers job from disk without re-applying."""
    pid = os.getpid()

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    job_id = meta["job_id"]
    op_id = meta["operation_id"]

    host_b = DurableFakeHost(host_state_dir=host_state_dir)
    assert host_b.mutation_count == 1  # Persisted on disk from Phase A

    # Track any unexpected calls to apply_operation
    apply_call_count = 0
    orig_apply = host_b.apply_operation

    def tracked_apply(*args, **kwargs):
        nonlocal apply_call_count
        apply_call_count += 1
        return orig_apply(*args, **kwargs)

    host_b.apply_operation = tracked_apply

    core_b = JobService(storage_root, project_root, host_b)

    # Resume job from disk
    resumed = core_b.resume_job(job_id)

    receipt = core_b.store.load_receipt(job_id, op_id)

    out = {
        "phase_a_pid": meta["phase_a_pid"],
        "phase_b_pid": pid,
        "job_id": job_id,
        "job_status": resumed.status.value,
        "receipt_status": receipt.status.value if receipt else None,
        "phase_b_apply_calls": apply_call_count,
        "final_mutation_count": host_b.mutation_count,
        "final_revision": host_b.current_revision,
        "verification_succeeded": resumed.status == JobStatus.COMPLETED,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    sys.exit(0)


def run_phase_a_crash_before(storage_root: Path, project_root: Path, host_state_dir: Path, meta_file: Path) -> None:
    """Phase A: Persists APPLYING but crashes before host call."""
    pid = os.getpid()

    test_model = project_root / "character.blend"
    test_model.write_text("v1_data", encoding="utf-8")

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
        operation_id="op_crash_before_sub",
        job_id=job.job_id,
        project_id="proj_1",
        host_instance_id="host_1",
        document_id="doc_1",
        tool="object.rename",
        mode=OperationMode.APPLY,
        target_ids=["Character"],
        expected_revision="rev_1",
        idempotency_key="idem_crash_before_sub",
        prepared_plan_ref="plan_1",
        checkpoint_ref=job.checkpoint_ref,
        arguments={"new_name": "Character_Redispatched"},
    )

    core_a.store.save_operation(op)
    job.status = JobStatus.APPLYING
    job.current_operation_id = op.operation_id
    core_a.store.save_job(job)

    meta = {
        "phase_a_pid": pid,
        "job_id": job.job_id,
        "operation_id": op.operation_id,
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    os._exit(43)


def run_phase_b_crash_before(storage_root: Path, project_root: Path, host_state_dir: Path, meta_file: Path, out_file: Path) -> None:
    """Phase B: Discovers NOT_FOUND, safe-redispatches, and completes with mutation_count == 1."""
    pid = os.getpid()

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    job_id = meta["job_id"]
    op_id = meta["operation_id"]

    host_b = DurableFakeHost(host_state_dir=host_state_dir, initial_revision="rev_1", next_revision="rev_2")
    core_b = JobService(storage_root, project_root, host_b)

    assert host_b.mutation_count == 0

    st = host_b.query_operation_status(op_id, "idem_crash_before_sub")
    assert st.state == HostStatusEnum.NOT_FOUND

    resumed = core_b.resume_job(job_id)

    receipt = core_b.store.load_receipt(job_id, op_id)

    out = {
        "phase_a_pid": meta["phase_a_pid"],
        "phase_b_pid": pid,
        "job_id": job_id,
        "job_status": resumed.status.value,
        "receipt_status": receipt.status.value if receipt else None,
        "final_mutation_count": host_b.mutation_count,
        "final_revision": host_b.current_revision,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        sys.stderr.write("Usage: process_restart_worker.py <mode> <storage_root> <project_root> <host_state_dir> [meta_file] [out_file]\n")
        sys.exit(1)

    mode = sys.argv[1]
    storage_root = Path(sys.argv[2])
    project_root = Path(sys.argv[3])
    host_state_dir = Path(sys.argv[4])

    if mode == "phase_a_ack_loss":
        meta_file = Path(sys.argv[5])
        run_phase_a_ack_loss(storage_root, project_root, host_state_dir, meta_file)
    elif mode == "phase_b_ack_loss":
        meta_file = Path(sys.argv[5])
        out_file = Path(sys.argv[6])
        run_phase_b_ack_loss(storage_root, project_root, host_state_dir, meta_file, out_file)
    elif mode == "phase_a_crash_before":
        meta_file = Path(sys.argv[5])
        run_phase_a_crash_before(storage_root, project_root, host_state_dir, meta_file)
    elif mode == "phase_b_crash_before":
        meta_file = Path(sys.argv[5])
        out_file = Path(sys.argv[6])
        run_phase_b_crash_before(storage_root, project_root, host_state_dir, meta_file, out_file)
    else:
        sys.stderr.write(f"Unknown mode: {mode}\n")
        sys.exit(1)
