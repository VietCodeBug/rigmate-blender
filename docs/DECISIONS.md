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


