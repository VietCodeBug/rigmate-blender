"""Test multi-process OS process restart ACK-loss recovery using separate child Python interpreters.

Proves:
- Phase A and Phase B execute in separate OS processes (phase_a_pid != phase_b_pid)
- Zero RAM state, global variables, or module caches survive between phases
- After Phase A crashes, Phase B recovers status from disk without duplicate apply
- Final mutation count remains strictly 1
- Authoritative NOT_FOUND in Phase B safely redispatches once to completion
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


WORKER_SCRIPT = Path(__file__).parent / "helpers" / "process_restart_worker.py"


def test_true_fresh_process_ack_loss_recovery(tmp_path):
    """
    Execute Phase A in one child Python process (simulated crash via os._exit(42)),
    then execute Phase B in a fresh child Python process.
    Assert phase_a_pid != phase_b_pid, apply_calls_in_b == 0, and mutation_count == 1.
    """
    storage_root = tmp_path / "storage"
    project_root = tmp_path / "project"
    host_state_dir = tmp_path / "host_state"
    meta_file = tmp_path / "phase_a_meta.json"
    out_file = tmp_path / "phase_b_out.json"

    storage_root.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)
    host_state_dir.mkdir(parents=True, exist_ok=True)

    # --- Phase A: Mutate on host, drop connection, exit(42) ---
    proc_a = subprocess.run(
        [
            sys.executable,
            str(WORKER_SCRIPT),
            "phase_a_ack_loss",
            str(storage_root),
            str(project_root),
            str(host_state_dir),
            str(meta_file),
        ],
        capture_output=True,
        text=True,
    )

    # Process A must terminate abnormally (code 42)
    assert proc_a.returncode == 42, f"Phase A failed with output: {proc_a.stderr}"
    assert meta_file.is_file(), "Phase A did not write metadata file"

    with open(meta_file, "r", encoding="utf-8") as f:
        meta_a = json.load(f)

    phase_a_pid = meta_a["phase_a_pid"]
    assert meta_a["mutation_count"] == 1

    # --- Phase B: Fresh Python interpreter startup recovery ---
    proc_b = subprocess.run(
        [
            sys.executable,
            str(WORKER_SCRIPT),
            "phase_b_ack_loss",
            str(storage_root),
            str(project_root),
            str(host_state_dir),
            str(meta_file),
            str(out_file),
        ],
        capture_output=True,
        text=True,
    )

    assert proc_b.returncode == 0, f"Phase B failed with output: {proc_b.stderr}\n{proc_b.stdout}"
    assert out_file.is_file(), "Phase B did not write output file"

    with open(out_file, "r", encoding="utf-8") as f:
        out_b = json.load(f)

    phase_b_pid = out_b["phase_b_pid"]

    # 1. Proves DIFFERENT Python OS processes!
    assert phase_a_pid != phase_b_pid, f"PIDs must be different! {phase_a_pid} == {phase_b_pid}"

    # 2. Phase B must NOT call apply_operation again!
    assert out_b["phase_b_apply_calls"] == 0, "Phase B must not call apply again!"

    # 3. Mutation count remains strictly 1!
    assert out_b["final_mutation_count"] == 1

    # 4. Job is completed with valid receipt
    assert out_b["job_status"] == "completed"
    assert out_b["receipt_status"] == "completed"
    assert out_b["verification_succeeded"] is True


def test_true_fresh_process_not_found_safe_redispatch(tmp_path):
    """
    Phase A crashes before calling host (os._exit(43)).
    Phase B launches in fresh Python process, queries host (receives NOT_FOUND),
    and safely redispatches the SAME operation to completion with mutation_count == 1.
    """
    storage_root = tmp_path / "storage"
    project_root = tmp_path / "project"
    host_state_dir = tmp_path / "host_state"
    meta_file = tmp_path / "phase_a_meta_crash.json"
    out_file = tmp_path / "phase_b_out_crash.json"

    storage_root.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)
    host_state_dir.mkdir(parents=True, exist_ok=True)

    proc_a = subprocess.run(
        [
            sys.executable,
            str(WORKER_SCRIPT),
            "phase_a_crash_before",
            str(storage_root),
            str(project_root),
            str(host_state_dir),
            str(meta_file),
        ],
        capture_output=True,
        text=True,
    )

    assert proc_a.returncode == 43

    with open(meta_file, "r", encoding="utf-8") as f:
        meta_a = json.load(f)

    phase_a_pid = meta_a["phase_a_pid"]

    proc_b = subprocess.run(
        [
            sys.executable,
            str(WORKER_SCRIPT),
            "phase_b_crash_before",
            str(storage_root),
            str(project_root),
            str(host_state_dir),
            str(meta_file),
            str(out_file),
        ],
        capture_output=True,
        text=True,
    )

    assert proc_b.returncode == 0, f"Phase B failed with output: {proc_b.stderr}\n{proc_b.stdout}"

    with open(out_file, "r", encoding="utf-8") as f:
        out_b = json.load(f)

    assert phase_a_pid != out_b["phase_b_pid"]
    assert out_b["final_mutation_count"] == 1
    assert out_b["job_status"] == "completed"
    assert out_b["receipt_status"] == "completed"
