# Architectural Decision Records (ADR)

This document tracks key architectural decisions, rationale, and technical trade-offs in RigMate.

---

## ADR-01: Local Bridge Authentication via Runtime State Discovery
- **Context**: The Bridge Server and Blender Add-on run as separate local processes. The Bridge must protect sensitive POST endpoints (`/chat`, `/cancel`, `/quota/manual`) against unauthorized access or browser CSRF without requiring manual copy-pasting of API keys by the user.
- **Decision**:
  - On Bridge startup, generate a cryptographic token using `secrets.token_hex(16)`.
  - Atomically write runtime state (`host`, `port`, `auth_token`, `pid`, `started_at`) to `%LOCALAPPDATA%\RigMate\bridge_state.json`.
  - The Blender Client automatically reads `bridge_state.json` during connection checks and request dispatches.
  - Stale state detection (`is_stale()`) verifies PID liveness and timestamp thresholds (12 hours).
  - Tokens are never committed to version control and never stored in workspace repositories.
- **Consequences**: Seamless zero-config user experience combined with authenticated request protection.

---

## ADR-02: Distribution Boundary Between Blender Python and External Python
- **Context**: Blender uses an embedded Python distribution. End users cannot easily install external compiled wheels or server dependencies (FastAPI, Uvicorn, PyTorch, Pytest) into Blender's internal environment.
- **Decision**:
  - Partition the codebase into two operational tiers:
    1. **Blender Add-on Runtime**: Runs within Blender Python, depending only on `bpy`, `mathutils`, Python standard libraries, and bundled packages: `rigmate.core` and `rigmate.storage`.
    2. **Bridge & MCP Server**: Runs in an external Python virtual environment containing FastAPI, Uvicorn, Pydantic, and MCP SDK.
  - `scripts/package_addon.py` bundles `core/` and `storage/` directly into the ZIP under the `rigmate/` root package so internal imports (`from rigmate.core...`) resolve cleanly in Blender.
- **Consequences**: 1-click add-on installation via Blender Preferences without external dependency errors.

---

## ADR-03: Strict Truthfulness in Quota & Energy Level Display
- **Context**: AI providers report rate limits and quotas under diverse paradigms (daily requests, monthly credits, token caps). Fabricating or guessing percentage values when machine-readable data is missing misleads the user.
- **Decision**:
  - Strictly differentiate three independent quantities:
    1. `last_tokens_used`: Turn-level token consumption (Prompt + Completion).
    2. `quota_remaining`: Account-level remaining balance.
    3. `plan_expiration`: Subscription expiration date (distinct from daily/monthly reset windows).
  - Explicitly label all data sources: `[Automatic]`, `[Manual Entry]`, or `[DEMO]`.
  - Return `Automatic quota data is unavailable` when machine-readable endpoints do not exist (`UNKNOWN` source).
  - Render the percentage slider only when both `remaining` and `total > 0` are confirmed.
- **Consequences**: High transparency and user trust with zero fabricated quota indicators.

---

## ADR-04: Session Continuity and Actual Request Cancellation
- **Context**: Conversational rig assistance requires multi-turn memory. Cancelling a request must abort execution on the server rather than merely resetting a client-side UI flag.
- **Decision**:
  - The Bridge issues a `session_id` on the initial turn. The add-on stores this in `props.active_session_id` and attaches it to subsequent messages.
  - Clicking "New Session" resets `active_session_id`.
  - Clicking "Stop" dispatches `POST /cancel` with `session_id`. `SessionManager` invokes `task.cancel()` on the running `asyncio.Task` before resetting the UI.
- **Consequences**: Proper multi-turn context retention and immediate server-side cancellation of long-running calls.

---

## ADR-05: English-First Canonical Codebase and Localization Layer
- **Context**: Open-source contributors and automated tools require a standard international technical baseline. Business logic must not hardcode specific regional languages.
- **Decision**:
  - English is the canonical language for source code, API contracts, developer documentation, logs, comments, docstrings, and internal errors.
  - User-facing text is localized via `rigmate.core.i18n.t(key, locale=...)`.
  - English (`en`) is the default and canonical fallback locale. Vietnamese (`vi`) is a first-class supported user-facing locale.
  - Logs MUST NOT be localized; logs remain English regardless of the UI language.
  - Error identifiers (`BridgeConnectionError`, `BridgeAuthError`) and error codes are separated from UI translations.
- **Consequences**: High international maintainability, extensible locale support, and zero hardcoded natural language strings in business logic.

---

## ADR-06: Unified Packaging Layout and Relative Imports in Blender Add-on
- **Context**: The source tree has add-on files in `src/rigmate/blender_addon/` while the packaged ZIP installs as the root add-on directory `rigmate/` inside Blender (`scripts/addons/rigmate/`). In earlier builds, absolute imports like `from rigmate.blender_addon.ui import ...` failed inside Blender because `rigmate.blender_addon` does not exist inside the packaged hierarchy.
- **Decision**:
  - Adopt a unified flattened root package layout in the ZIP:
    ```text
    rigmate/
        __init__.py
        ui.py
        operators.py
        client.py
        bpy_inspectors.py
        core/
        storage/
    ```
  - Standardize all internal add-on cross-imports to Python relative imports (e.g. `from .ui import ...`, `from .bpy_inspectors import ...`, `from .client import ...`).
  - Standardize subpackage imports as root package imports (`from rigmate.core...`, `from rigmate.storage...`).
  - Automate import validation via `tests/test_package_smoke.py`, which builds the ZIP, unzips to a clean temporary directory, and verifies module resolution outside Blender using a controlled stub `bpy`.
- **Consequences**: Zero divergence between packaging and source; guaranteed import resolution inside standard Blender installations.

---

## ADR-07: Machine-Readable Structured Error Identifiers
- **Context**: In conversational AI workflows, translating raw error strings or matching natural language substrings leads to fragile error handling.
- **Decision**:
  - Centralize canonical error codes (`HOST_UNAVAILABLE`, `CHECKPOINT_FAILED`, `QUOTA_EXHAUSTED`, etc.) in `src/rigmate/core/errors.py`.
  - Internal exception messages and logging remain strictly English.
  - UI translations route exclusively through machine-readable error codes (`t(f"error.{code}")`) and never drive business or branching logic.
- **Consequences**: Deterministic error dispatch, zero localized string dependencies in business code.

---

## ADR-08: Timezone-Aware Canonical UTC Persistence
- **Context**: Timestamps originating from multi-machine or local environments often cause desynchronization or ambiguity when local offsets are omitted.
- **Decision**:
  - Enforce timezone-aware UTC datetime instances across all models, journals, and receipts.
  - Protocol persistence strictly uses canonical ISO 8601 strings ending in `Z` (e.g. `2026-09-17T08:00:00Z`).
  - Naive datetimes are rejected at conversion boundaries (`src/rigmate/core/time_utils.py`).
- **Consequences**: Consistent ordering across event streams, journals, and client synchronization.

---

## ADR-09: Operation vs. Receipt Boundary Separation
- **Context**: Conflating an execution intent with its verified outcome causes false assumptions about tool success.
- **Decision**:
  - Separate tool execution intent into `OperationEnvelope` (`src/rigmate/core/operations.py`) and verified result into `OperationReceipt` (`src/rigmate/core/receipts.py`).
  - In `apply` mode, an operation envelope strictly requires `prepared_plan_ref` and `checkpoint_ref` (except `checkpoint.create`).
  - An operation receipt requires post-execution verification before reaching `completed` status.
- **Consequences**: Prevents unverified mutation assumptions; aligns with the RigMate Blueprint contract.

---

## ADR-10: Evidence-Based Capability Declaration
- **Context**: Inferring tool support merely from the existence of an executable or binary creates unreliable execution failures.
- **Decision**:
  - System and provider capabilities are explicitly registered with verifiable evidence (`CapabilityRegistry` in `src/rigmate/core/capabilities.py`, `ProviderCapabilities` in `src/rigmate/providers/capabilities.py`).
  - Unknown capabilities default to unavailable/false.
- **Consequences**: Trustworthy execution boundaries and clean preflight capability checks.

---

## ADR-11: Repository Ignore Pattern Safety & Root-Scoping
- **Context**: In an earlier build, a broad `.gitignore` pattern `storage/` inadvertently matched the application source directory `src/rigmate/storage/`, preventing core storage source files (`manager.py`, `paths.py`, `retention.py`, `json_io.py`, `disk_budget.py`) from being tracked in Git while local tests continued to pass from untracked working-tree files.
- **Decision**:
  - All repository ignore patterns targeting runtime data directories must be root-scoped (e.g. `/storage/`) or scoped explicitly to runtime data paths (`/local_data/`, `%LOCALAPPDATA%/RigMate/`).
  - Never use unanchored generic directory names in `.gitignore` that could collide with package module subdirectories.
  - Implement automated repository integrity checks (`tests/test_repository_integrity.py` and `scripts/check_repo_integrity.py`) to verify that all architectural source modules are present and tracked by Git.
- **Consequences**: Eliminates silent omissions of source code in fresh repository checkouts.

---

## ADR-12: Closed-Loop Execution Lifecycle, Event Journaling, and Checkpoint Engine
- **Context**: Relying on in-memory state or believing tool execution success without postcondition verification risks silent failure, unacknowledged mutation side-effects (ACK loss), or data corruption after process restarts. Furthermore, RigMate does not provide a distributed ACID transaction across Blender, Godot, filesystem, and external AI providers.
- **Decision**:
  - Implement a closed-loop execution lifecycle governed by a strict canonical state machine (`JobStatus`) and an append-only event journal (`events.jsonl`).
  - Preconditions are verified before apply. A pre-mutation snapshot is created using content-addressed blob storage (`.rigmate/blobs/xx/hash`).
  - Document mutation operations require a local document-level writer lock (`.rigmate/locks/`). Document mutation locks are NEVER held while waiting for external AI responses, user inputs, or external agent planning.
  - Operation idempotency is tracked durably with canonical request hashing (`.rigmate/idempotency/`).
  - If a network drop or crash occurs after host mutation (ACK loss), the system queries host operation status via `query_status()` before deciding between `verifying` and `recovery_required`. It NEVER blindly reapplies.
  - Recovery restores preserved files to verified non-destructive copies (`<name>.recovered.<timestamp>.<ext>`) without destructive live overwriting.
- **Consequences**: Deterministic, inspectable, and crash-recoverable execution without invisible state.

---

## ADR-13: Standard-Library Dependency Boundary for Blender Add-on
- **Context**: Blender uses an embedded, isolated Python distribution without pip-installed wheels by default. In earlier iterations, bundling `rigmate.core` into the add-on ZIP dragged in Pydantic, FastAPI, and other external dependencies, leading to registration errors (`ModuleNotFoundError: No module named 'pydantic'`) unless users polluted their Blender environment with external wheels.
- **Decision**:
  - The Blender add-on (`src/rigmate/blender_addon/`) must strictly depend ONLY on Python standard libraries (`dataclasses`, `pathlib`, `json`, `urllib`, `threading`, `typing`) and Blender APIs (`bpy`, `mathutils`).
  - Add-on DTOs (`src/rigmate/blender_addon/dto.py`) are implemented as pure stdlib dataclasses with `.to_dict()` and `.model_dump()` serialization helpers.
  - Localization (`i18n.py`), scene diagnostics (`analyzer.py`), and runtime state discovery (`client.py`) are implemented self-contained within the add-on module.
  - `rigmate.core` re-exports canonical classes from `blender_addon.dto` to guarantee 100% schema alignment across Bridge, CLI, and add-on.
  - Packaging (`scripts/package_addon.py`) enforces an explicit allowlist, packaging only the 8 required add-on files into the ZIP without external dependencies.
- **Consequences**: Guaranteed out-of-the-box installation on any vanilla Blender 4.x/5.x distribution without any external pip requirements.

---

## ADR-14: Dual-Import Fallback for Model Context Protocol (MCP) SDK 2.x
- **Context**: Upgrading dependencies brought in `mcp 2.2.0`, which refactored its server module and renamed `FastMCP` to `MCPServer`, breaking imports in `src/rigmate/mcp_server/server.py`.
- **Decision**:
  - Implement a dual-import fallback in `src/rigmate/mcp_server/server.py`:
    ```python
    try:
        from mcp.server.fastmcp import FastMCP
    except (ImportError, ModuleNotFoundError):
        from mcp.server.mcpserver import MCPServer as FastMCP
    ```
- **Consequences**: Backward and forward compatibility across `mcp 1.x` and `mcp 2.x` environments without breaking server initialization.

---

## ADR-15: Headless Host Control Plane, Neutral HostAdapter Protocol, and Durable Fake Host
- **Context**: RigMate execution control plane testing must be completely decoupled from Blender binary availability. Running real Blender tests on machines without Blender is impossible and would block continuous integration. At the same time, naive in-memory mocks fail to prove crash recovery, persistence, or ACK-loss guarantees.
- **Decision**:
  - Define a transport-neutral host control plane (`src/rigmate/core/host_protocol.py`) with zero `bpy`, `fastapi`, or `mcp` imports.
  - Model clear boundaries: `HostIdentity`, `DocumentIdentity`, `InspectionRequest`, `InspectionResult`, `PreparedHostOperation`, `HostApplyResult`, and `HostVerificationResult`.
  - Enforce explicit distinction between immediate mutation execution (`HostApplyResult`) and verified completion (`OperationReceipt`). A host apply return does not equate to job completion.
  - Implement a filesystem-backed `DurableFakeHost` (`src/rigmate/testing/durable_host.py`) persisting documents, revisions, mutation counts, operations, and idempotency records to disk.
  - Prove that destroying both `JobService` and `DurableFakeHost` in RAM and restoring from disk recovers operation status, prevents duplicate mutation, and keeps the mutation count strictly at 1.
- **Consequences**: Complete headless proof of the entire closed-loop control plane. Real Blender work is cleanly constrained to implementing `RealBlenderHostAdapter` on the target Blender machine.

---

## ADR-16: Neutral Pure-Stdlib Contracts Layer & Inverted Dependencies
- **Context**: In earlier versions, `core/dto.py`, `core/analyzer.py`, and `core/i18n.py` imported from `rigmate.blender_addon.*`. This inverted architectural boundaries: Core depended on Blender-specific code, and `HostAdapter` depended on Pydantic `OperationEnvelope`, making it impossible for a vanilla Blender runtime to import contracts cleanly.
- **Decision**:
  - Establish `src/rigmate/contracts/` (`dto.py`, `host.py`, `hashing.py`) as a pure Python standard library package (dataclasses, typing, hashlib, json).
  - Relocate deterministic rig diagnosis to `src/rigmate/analysis/rig.py` and localization to `src/rigmate/localization/engine.py`.
  - Invert dependencies: Core and Blender Add-on both depend inward on `rigmate.contracts`, `rigmate.analysis`, and `rigmate.localization`.
  - Zero non-Blender runtime modules may import `rigmate.blender_addon`.
  - Define `HostOperationRequest` as a pure stdlib dataclass for the host protocol; provide `host_request_from_operation(op)` at the Core adapter boundary to convert Core Pydantic `OperationEnvelope` instances.
- **Consequences**: Pure standard library boundary; zero Pydantic requirement on the host runtime; Core is strictly decoupled from Blender.

---

## ADR-17: Authoritative Host Operation Status & Crash-Before-Apply Redispatch Invariants
- **Context**: Previously, `query_operation_status()` returned `Optional[HostApplyResult]`, collapsing `NOT_FOUND`, `UNKNOWN`, and `UNAVAILABLE` into `None`. In crash-before-apply scenarios, Core could not distinguish whether an operation was never received or whether the query simply timed out.
- **Decision**:
  - Introduce explicit `HostOperationStatus` enum (`ACCEPTED`, `EXECUTING`, `EXECUTED`, `FAILED`, `NOT_FOUND`, `UNKNOWN`, `UNAVAILABLE`).
  - Reserve `NOT_FOUND` strictly for authoritative proof that the host registry was searched and contains no record of the operation.
  - Require that `UNKNOWN` and `UNAVAILABLE` never trigger re-apply, leading instead to `RECOVERY_REQUIRED`.
  - Permit safe redispatch on `NOT_FOUND` only after re-validating the exact same `operation_id`, `idempotency_key`, request hash, verified plan/checkpoint, re-acquired writer lock, and current document revision.
- **Consequences**: Deterministic crash-before-apply recovery without risk of duplicate mutations or silent side-effects.

---

## ADR-18: Multi-Process OS Subprocess ACK-Loss Verification
- **Context**: Testing crash recovery by destroying and recreating objects (`del core; del host`) within the same Python process proves memory reconstruction from disk, but fails to prove true OS process restart resilience (e.g. absence of shared interpreter state, static class variables, or module caches).
- **Decision**:
  - Implement automated multi-process tests (`tests/test_process_restart_subprocess.py` and `tests/helpers/process_restart_worker.py`) using `sys.executable` and `subprocess`.
  - Execute Phase A in an independent child process that mutates the durable host and crashes via `os._exit(42)` before Core persists the receipt.
  - Execute Phase B in a completely separate child process (`phase_a_pid != phase_b_pid`) that recovers state from disk, detects `EXECUTED` status, skips apply, verifies postconditions, and completes the job.
  - Assert that `phase_b_apply_calls == 0` and total host mutations remain strictly 1.
- **Consequences**: Irrefutable proof of true OS process restart safety across real process lifecycles.






