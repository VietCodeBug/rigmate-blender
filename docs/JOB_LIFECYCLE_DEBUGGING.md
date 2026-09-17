# Job Lifecycle Forensic Debugging Guide

This document explains how to inspect, understand, and debug RigMate V1 jobs using persisted storage artifacts after a process interruption or unexpected outcome.

---

## 1. Storage Directory Layout

Every job persisted by RigMate writes directly to the local filesystem without relying on in-memory state:

```text
<project_root>/.rigmate/
├── jobs/
│   └── <job_id>/
│       ├── job.json            # Materialized job state record
│       ├── plan.json           # Prepared execution plan
│       ├── events.jsonl        # Chronological event journal (append-only)
│       ├── operations/
│       │   └── <op_id>.json    # Persisted operation envelopes (intent)
│       ├── receipts/
│       │   └── <op_id>.json    # Persisted operation receipts (verified outcome)
│       └── recovery.json       # Startup recovery decision record (if crash occurred)
├── checkpoints/
│   └── <checkpoint_id>/
│       └── manifest.json       # Preserved files, source revision, blob references
├── blobs/
│   └── <prefix>/
│       └── <sha256>            # Content-addressed deduplicated file data
├── idempotency/
│   └── <idempotency_key>.json  # Cached operation request hash and receipts
└── locks/
    └── <project_id>_<doc>.lock # Single-writer mutual exclusion lock
```

---

## 2. Correlating Identifiers

To trace a request flow from initial prompt through verification:
1. `job_id`: Prefix `job_` — Unique identifier for the entire job lifecycle.
2. `correlation_id`: Prefix `corr_` — Shared across all events, logs, and sub-operations belonging to the same user action.
3. `operation_id`: Prefix `op_` — Identifier for an individual tool invocation envelope.
4. `checkpoint_id`: Prefix `cp_` — Identifier for the pre-mutation snapshot.

---

## 3. Detecting and Investigating Fault Scenarios

### A. ACK-Loss Scenario
- **Symptoms**: Process crashed or network dropped during `applying`.
- **Forensic Evidence**:
  - `events.jsonl` contains `operation.apply_started`, followed by `operation.apply_interrupted`.
  - `recovery.json` or host status check reveals that the host *did* perform the mutation and has a stored receipt.
  - Check `idempotency/<key>.json`: It contains the recorded receipt and deterministic `request_hash`.
  - RigMate will NOT call apply again. Mutation count remains strictly 1.

### B. Recovery Required (`recovery_required`)
- **Symptoms**: Job ended in `recovery_required` status.
- **Forensic Evidence**:
  - Check `job.json`: `error.code` will often be `RESULT_UNVERIFIED` or `TARGET_STALE`.
  - Check `receipts/<op_id>.json`: `status` may show `failed`, or postcondition verification failed (e.g. host revision did not advance).
  - Check `recovery.json`: Recommends `restore_from_checkpoint`.
  - **Remediation**: Invoke `JobService.recover_job(job_id)` to restore preserved files from content-addressed blob storage to non-destructive copies (`character.recovered.<timestamp>.blend`). Live user files are never blindly overwritten.

### C. Stale Revision Precondition (`TARGET_STALE`)
- **Symptoms**: Job fails before executing mutation.
- **Forensic Evidence**:
  - `job.json` expected revision differs from the document revision reported by host `executor.prepare()`.
  - `events.jsonl` does NOT contain `operation.apply_started`.
  - Host mutation counter is 0. Checkpoint remains preserved.

### D. Telling Apply Success from Verified Success
- In RigMate, `apply()` returning HTTP 200 or tool returning `success` is NOT considered job completion.
- Inspect `events.jsonl`:
  - `operation.receipt_recorded`: Tool finished running on host.
  - `job.verify_started` -> `job.verify_succeeded` -> `job.completed`: Host state (revision, facts, changes) was independently proven.

---

## 4. Rebuilding Job Timelines

To generate a human-readable chronology for any job:
```python
from rigmate.core.timeline import build_job_timeline, format_timeline_text
from rigmate.storage.job_store import JobStore

store = JobStore(".rigmate")
timeline = build_job_timeline("job_xxx", store)
print(format_timeline_text(timeline))
```

Example timeline output:
```text
000 2026-09-17T10:00:00Z [job.created] (mutation)
001 2026-09-17T10:00:01Z [job.inspect_started] (queued -> inspecting)
002 2026-09-17T10:00:02Z [checkpoint.requested] (cp=cp_abc)
003 2026-09-17T10:00:02Z [checkpoint.created] (cp=cp_abc)
004 2026-09-17T10:00:03Z [job.prepared] (inspecting -> prepared)
005 2026-09-17T10:00:04Z [operation.apply_started] (prepared -> applying, op=op_1)
006 2026-09-17T10:00:05Z [operation.receipt_recorded] (op=op_1)
007 2026-09-17T10:00:05Z [job.verify_started] (applying -> verifying, op=op_1)
008 2026-09-17T10:00:06Z [job.verify_succeeded] (op=op_1)
009 2026-09-17T10:00:06Z [job.completed] (verifying -> completed)
```
