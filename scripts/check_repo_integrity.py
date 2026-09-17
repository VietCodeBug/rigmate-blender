"""Developer script verifying Git tracking integrity of required source modules."""

import subprocess
import sys
from pathlib import Path

REQUIRED_TRACKED_FILES = [
    "src/rigmate/storage/__init__.py",
    "src/rigmate/storage/paths.py",
    "src/rigmate/storage/manager.py",
    "src/rigmate/storage/runtime_state.py",
    "src/rigmate/storage/retention.py",
    "src/rigmate/storage/json_io.py",
    "src/rigmate/storage/disk_budget.py",
    "src/rigmate/storage/job_store.py",
    "src/rigmate/storage/checkpoints.py",
    "src/rigmate/storage/idempotency.py",
    "src/rigmate/core/errors.py",
    "src/rigmate/core/ids.py",
    "src/rigmate/core/time_utils.py",
    "src/rigmate/core/events.py",
    "src/rigmate/core/operations.py",
    "src/rigmate/core/receipts.py",
    "src/rigmate/core/capabilities.py",
    "src/rigmate/core/support_bundle.py",
    "src/rigmate/core/json_types.py",
    "src/rigmate/core/jobs.py",
    "src/rigmate/core/plans.py",
    "src/rigmate/core/checkpoints.py",
    "src/rigmate/core/executors.py",
    "src/rigmate/core/lock.py",
    "src/rigmate/core/recovery.py",
    "src/rigmate/core/timeline.py",
    "src/rigmate/core/job_service.py",
]


def check_repo_integrity() -> bool:
    root_dir = Path(__file__).resolve().parent.parent
    try:
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = set(res.stdout.replace("\\", "/").splitlines())
    except Exception as e:
        print(f"[ERROR] Failed to run git ls-files: {e}")
        return False

    missing = []
    for req in REQUIRED_TRACKED_FILES:
        norm_req = req.replace("\\", "/")
        if norm_req not in tracked_files:
            missing.append(norm_req)

    if missing:
        print("[FAIL] The following required files are NOT tracked by Git:")
        for m in missing:
            print(f"  - {m}")
        return False

    print(f"[PASS] All {len(REQUIRED_TRACKED_FILES)} required source files are verified tracked in Git.")
    return True


if __name__ == "__main__":
    success = check_repo_integrity()
    sys.exit(0 if success else 1)
