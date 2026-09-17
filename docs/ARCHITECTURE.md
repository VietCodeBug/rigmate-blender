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
