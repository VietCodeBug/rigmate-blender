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
  - Canonical language for source code, comments, docstrings, internal errors, exception classes, logs, and technical documentation is strictly English.
  - End-user facing UI strings, reports, and dialogs are routed through `rigmate.core.i18n.t(key, locale=...)`.
  - English (`en`) is the default and fallback locale. Vietnamese (`vi`) is a first-class supported locale.
- **Consequences**: High international maintainability, extensible locale support, and zero hardcoded natural language strings in business logic.
