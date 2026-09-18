# RigMate System Architecture

This document describes the current architecture of RigMate v0.1 following integration and internationalization stabilization.

---

## 1. Architectural Principles

1. **Clear Boundary Between Blender Python and External Python**:
   - **Blender Python**: Runs the Add-on UI, Operators, Background Client, and two self-contained packages bundled inside the ZIP: `rigmate.core` and `rigmate.storage`.
   - **External Python**: Runs the Bridge Server (FastAPI/Uvicorn), MCP Server (FastMCP), and AI Provider adapters (MockAIProvider, AntigravityProvider).

2. **Local Authentication via Runtime Discovery Token (Zero-Config Security)**:
   - The Bridge binds strictly to `127.0.0.1`.
   - On startup, it generates a cryptographically secure token (`secrets.token_hex(16)`) and atomically writes runtime state to `%LOCALAPPDATA%\RigMate\bridge_state.json`.
   - The Blender Client automatically reads this file to sign requests with the `x-rigmate-token` header on sensitive endpoints (`/chat`, `/cancel`, `/quota`, `/quota/manual`).

3. **Thread Safety & Non-blocking I/O**:
   - All network communications within Blender execute on background daemon threads via `RigMateBridgeClient`.
   - Results are dispatched back to Blender's Main Thread using `bpy.app.timers.register`.

4. **Lean Context Inspection**:
   - The `send_selected_only` toggle collects high-level summary info via `BpyInspector.get_selected_context()` (active object, modifiers, vertex count, transforms). 50k vertex coordinates are never transmitted over the wire.

5. **Canonical English Technical Core & i18n Localization**:
   - Source comments, docstrings, error messages, exception types, and server logs are strictly canonical English.
   - User-facing UI labels, dialogs, and reports query the internationalization layer `rigmate.core.i18n.t(key, locale=...)`. English is the default locale (`en`), with Vietnamese (`vi`) fully supported.

---

## 2. Component Diagram

```text
+-------------------------------------------------------------------------+
|                              BLENDER PROCESS                            |
|                                                                         |
|  [3D Viewport] <---> [RigMate Sidebar UI (Tab N)]                       |
|                              |                                          |
|                 [Operators (Main Thread)]                               |
|                              |                                          |
|               [BpyInspector.get_selected_context()]                     |
|                              |                                          |
|         [RigMateBridgeClient (Background Daemon Thread)]                |
|               ^                                                         |
|               | (Auto-discover runtime auth_token)                      |
|               |                                                         |
|         [%LOCALAPPDATA%/RigMate/bridge_state.json]                      |
+------------------------------|------------------------------------------+
                               | (HTTP / JSON localhost:8765)
                               | [Headers: x-rigmate-token]
                               v
+-------------------------------------------------------------------------+
|                         RIGMATE BRIDGE PROCESS                          |
|                                                                         |
|  [FastAPI Bridge Server (127.0.0.1)]                                    |
|         |                                                               |
|         +---> [RuntimeStateManager] -> writes bridge_state.json         |
|         |                                                               |
|         +---> [SessionManager] (Session continuity & task cancellation) |
|         |                                                               |
|         +---> [StorageManager] (Atomic writes, corrupt backups, Quota)  |
|         |                                                               |
|         +---> [AI Provider Dispatcher]                                  |
|                     |                                                   |
|                     +---> [MockAIProvider] (Hunyuan+Meshy scenarios)    |
|                     |                                                   |
|                     +---> [AntigravityProvider] (Adapter agy / SDK)     |
|                                                                         |
|  [MCP Server (FastMCP - Model Context Protocol)]                        |
|         +--- inspect_scene                                              |
|         +--- inspect_mesh                                               |
|         +--- inspect_armature                                           |
|         +--- diagnose_rig                                               |
+-------------------------------------------------------------------------+
```

---

## 3. Closed-Loop Execution Lifecycle & Checkpoint Engine

RigMate enforces a strictly verifiable, crash-recoverable execution lifecycle for all mutation-capable jobs.

```text
       [queued]
          |
    [inspecting] <---> [needs_input]
          |
     [prepared] (preconditions verified + checkpoint acquired)
          |
      [applying] (under document single-writer lock)
      /        \
 [verifying]   [cancel_requested]
   /       \          |
[completed] [recovery_required]
                 |
            [recovered] (restored to non-destructive copy)
```

### Execution Invariants
1. **Pre-mutation Checkpoint**: Before entering `applying`, all authorized target files are snapshotted to content-addressed blobs (`.rigmate/blobs/xx/hash`) with preflight disk budget verification.
2. **Durable Event Journal**: All transitions append monotonic events to `.rigmate/jobs/<job_id>/events.jsonl` prior to atomic `job.json` updates.
3. **Idempotency & ACK-Loss Protection**: Operations are tracked in `.rigmate/idempotency/` via canonical SHA-256 request hashes. If network drops after host mutation, `query_status()` discovers the executed mutation and prevents duplicate re-apply.
4. **Verified Outcome**: `completed` strictly requires host postcondition verification (`verified_at` and `host_revision_after`).
5. **Non-Destructive Recovery**: Restoring from a checkpoint materializes files to `<name>.recovered.<timestamp>.<ext>`, verifying restored hashes against the manifest without destructively overwriting live files.

---

## 4. Neutral Contracts & Headless Host Control Plane

RigMate enforces strict architectural isolation between the host runtime (Blender add-on or Godot) and the external Core execution lifecycle.

### Dependency Direction

```text
                     rigmate.contracts
                 (Pure Python Standard Library)
                 - dto.py
                 - host.py
                 - hashing.py
                        ^
                        |
          +-------------+-------------+
          |                           |
     blender_addon                   core
     (bpy adapter)              (Jobs / Lifecycle)
          |                           |
          +-------------+-------------+
                        |
             rigmate.analysis / rigmate.localization
                 (Pure Python Standard Library)
```

**Architectural Invariants:**
- `rigmate.contracts`, `rigmate.analysis`, and `rigmate.localization` are **100% pure Python standard library** (zero imports of `pydantic`, `fastapi`, `mcp`, `httpx`, `bpy`, `mathutils`, `storage`, `core`, or `blender_addon`).
- **Core imports Blender Addon:** `NO`. Core strictly imports neutral contracts, analysis, and localization.
- **Blender imports Core:** `NO`. Blender add-on runs self-contained with neutral packages.
- **HostAdapter protocol requires Pydantic:** `NO`. Protocol methods accept `HostOperationRequest`, a pure standard library dataclass.
- **Core adapter boundary:** `host_request_from_operation(op: OperationEnvelope) -> HostOperationRequest` translates Core Pydantic envelopes to neutral transport requests at the Core dispatch boundary.

### Host Operation Status & Recovery Semantics

`HostAdapter.query_operation_status(operation_id, idempotency_key)` returns a structured `HostOperationStatus`:

| State | Durable Evidence Requirement | Core Recovery Action | Redispatch Allowed? |
| :--- | :--- | :--- | :--- |
| **`ACCEPTED`** | Host durably logged identity; execution not proven | Preserve in-progress state; do NOT re-apply | `NO` |
| **`EXECUTING`** | Host actively executing operation | Preserve in-progress state; await completion | `NO` |
| **`EXECUTED`** | Durable host registry proves execution; apply evidence attached | Advance to `verifying`; verify postconditions; complete if valid | `NO` (already run) |
| **`FAILED`** | Host durably records execution failure | Do not assume zero side-effects; transition to safe failure/recovery | `NO` |
| **`NOT_FOUND`** | Registry authoritatively queried and proves operation never accepted | Validate invariants (same op/idempotency/hash/revision/checkpoint); redispatch SAME operation | **`YES` (ONLY state)** |
| **`UNKNOWN`** | Host reachable but cannot prove execution state | Transition to `RECOVERY_REQUIRED`; do NOT re-apply | `NO` |
| **`UNAVAILABLE`** | Transport timeout or host communication failure | Transition to `RECOVERY_REQUIRED` / retry probe; NEVER re-apply | `NO` |

### Authoritative NOT_FOUND & Crash-Before-Host-Call Invariant

If Core crashes after persisting `APPLYING` but before the host receives or accepts the operation:
1. Upon restart, Core reconciliation queries `query_operation_status()`.
2. The host registry is authoritatively searched and returns `NOT_FOUND` (proving zero mutations occurred).
3. Core re-validates:
   - Persisted `operation_id` matches.
   - Persisted `idempotency_key` matches.
   - Canonical request hash matches.
   - Prepared plan and checkpoint manifest remain verified.
   - Document writer lock is re-acquired.
   - Current host document revision equals `expected_revision`.
4. If all invariants hold, Core safely redispatches the **SAME** operation identity once.
5. If the host revision changed in the interim, Core transitions to `TARGET_STALE` with zero side effects.

### Separation of Apply vs. Verification
A host returning from `apply_operation` yields a `HostApplyResult` (confirming mutation execution). This is strictly distinct from verified completion:
- **`HOST EXECUTED` != `VERIFIED` != `JOB COMPLETED`**
- `OperationReceipt.status` strictly uses `ReceiptStatus`.
- `JobRecord.status` strictly uses `JobStatus`.
- Final `OperationReceipt` with `status=completed` is only created after `verify_operation` passes postcondition verification (`verified_at` and `host_revision_after`).

### Verification Distinction: Object Reconstruction vs. True Process Restart

RigMate distinguishes two levels of recovery verification:
1. **Fresh Object Reconstruction**: Proves destruction of RAM objects (`del core; del host`) and reconstitution from disk within the same Python interpreter.
2. **Real Python Process Restart**: Proves separate OS child processes (`sys.executable` via `subprocess`) where Phase A crashes (`os._exit(42)`) and Phase B recovers in a distinct PID (`phase_a_pid != phase_b_pid`), verifying zero shared memory, zero module-level cache, and strictly 1 host mutation.

---

## 5. Mesh Preparation Architecture ("Kiểm tra & sửa lưới")

The **Mesh Preparation** module integrates directly into RigMate's closed-loop lifecycle without introducing competing state machines or parallel lifecycles.

### Component Placement

```text
       [Blender Viewport / Context]
                    |
                    v
    [bpy_inspectors.py (BpyInspector)]   <-- Reads live BMesh & scene state
                    |
                    v  (Standard DTOs: MeshInfo, SceneInfo)
       [rigmate.contracts.dto]           <-- Pure stdlib data models
                    |
                    v
         [rigmate.analysis]              <-- Deterministic pure Python rules & heuristics
                    |                        (No bpy, No Pydantic, Runs headlessly)
                    v  (Finding models, severity classification)
          [RigMate Core / Jobs]          <-- Plans, Checkpoints, Document Locks,
                    |                        Idempotency, Recovery, Receipt verification
                    v
          [HostAdapter Protocol]         <-- Dispatches typed HostOperationRequest to host
```

### Architectural Guarantees for Mesh Preparation
1. **Module Independence**: Pure geometric diagnostic logic and classification algorithms reside in `rigmate.analysis`, enabling 100% headless test execution on CI machines without Blender.
2. **Region Revision Safety (`REGION_STALE`)**: A sub-mesh region reference captured at document revision $N$ is strictly invalidated if any topology-changing operation increments revision to $N+1$. Stale vertex or face indices are NEVER blindly re-used.
3. **Dirty Document Guard**: If an active Blender scene has unsaved changes (`bpy.data.is_dirty == True`), Core halts prior to checkpoint creation and issues `NEEDS_INPUT`, preventing silent snapshotting of stale on-disk `.blend` files.
4. **AI Data Boundary**: Massive 3D vertex coordinate arrays are NEVER sent over the wire to external LLM providers. AI providers reason strictly over structured diagnostic summaries, finding IDs, and region labels.
5. **Decoupled 2D Godot Engine Workflow**: 2D Godot companion workflows (sprite animation, 2D bone deformation) remain 100% functional without Blender or 3D mesh modules installed.



