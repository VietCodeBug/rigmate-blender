# Project Status & Current State

This document provides a factual assessment of the current state of RigMate v0.1.

---

## 1. Environment Status
- **Local Machine Blender**: `REAL BLENDER TEST: NOT PERFORMED` (Blender is not installed on this headless agent environment).
- **Antigravity CLI**: `REAL ANTIGRAVITY CLI: UNVERIFIED` (Neither `agy` CLI nor `google.antigravity` package is verified in this worker; fallback adapter active).
- **Packaged Python Import Test**: `PACKAGED PYTHON IMPORT TEST: PASSED` (`tests/test_package_smoke.py` extracts ZIP to temp environment and verifies clean import resolution of all packaged modules).
- **Pure Python Automated Tests**: **98/98 tests PASSED** (100% test pass rate across analyzer, quota, providers, bridge auth, session flow, runtime state, storage, package smoke, i18n, path safety, file hashing, schema versions, project manifest, capabilities, redaction, retry, retention, structured errors, IDs, UTC time, JSON/JSONL I/O, events, operations, receipts, capability registry, disk budget, support bundle, and JSON types).

---

## 2. Completed Milestones
- **Core Diagnostics**:
  - Vertex density analysis tailored for Hunyuan 3D (~50k vertices) targeting Godot Engine.
  - Transform verification (unapplied scale/rotation on meshes and armatures).
  - Non-dogmatic finger bone heuristics.
- **Quota & Energy Bar**:
  - Distinct separation of turn token usage, account quota, and plan expiration.
  - Pure helper functions (`is_quota_exhausted`, `is_quota_available`, `calculate_valid_percentage`).
  - Machine-readable source verification (`[AUTOMATIC]`, `[MANUAL]`, `[DEMO]`, `UNKNOWN`, `UNSUPPORTED`).
  - Stale data detection (>24h threshold).
- **Pure Python Supporting Infrastructure Batch 1 (Partial Requirement Support)**:
  - **Path Safety** (`src/rigmate/core/path_safety.py`): Canonicalizes paths, verifies authorization within project roots, and rejects `..` traversal escapes (supports NFR-005, FR-003, FR-054; full cross-project mutation protection remains incomplete).
  - **File Hashing & Metadata** (`src/rigmate/core/file_hash.py`): Chunked streaming SHA-256 computation and strict verification for immutable artifacts (supports FR-003, FR-026, FR-036, FR-050, FR-052, FR-054).
  - **Schema Versioning** (`src/rigmate/core/schema_version.py`): Lightweight SemVer parser distinguishing SUPPORTED, READ_ONLY, and UNSUPPORTED versions without heavy dependencies (supports NFR-007, FR-056).
  - **Project Manifest** (`src/rigmate/core/project.py`): Baseline Pydantic project model enforcing `database_mode='none'` and `rigmate_account_required=False` (supports FR-001, FR-003; full Project Manager UI remains incomplete).
  - **Provider Capabilities** (`src/rigmate/providers/capabilities.py`): Fine-grained capability matrix requiring explicit evidence (official doc, probe, response, mock) before enabling features (supports FR-013, FR-014, FR-015, FR-056).
  - **Data Redaction** (`src/rigmate/core/redaction.py`): Non-mutating recursive scrubbing of auth tokens, API keys, and passwords for support bundles (supports FR-054, FR-060, NFR-009).
  - **Bounded Retry** (`src/rigmate/core/retry.py`): Deterministic exponential backoff calculation bounded at max 10 attempts for idempotent read/network probes (supports NFR-012, FR-024).
  - **Retention Policy Calculator** (`src/rigmate/storage/retention.py`): Pure logic calculating checkpoint cleanup candidates under count and byte budgets while protecting pinned and active-job snapshots (supports future checkpoint engine without deletion side-effects).
- **Pure Python Supporting Infrastructure Batch 2 (Partial Requirement Support)**:
  - **Structured Error Model** (`src/rigmate/core/errors.py`): Canonical machine-readable codes (`HOST_UNAVAILABLE`, `CHECKPOINT_FAILED`, `QUOTA_EXHAUSTED`, etc.), causality wrapping, and JSON serialization (supports NFR-009, NFR-014, FR-027).
  - **ID Generation** (`src/rigmate/core/ids.py`): Canonical UUID-based prefixed identifiers (`proj_`, `job_`, `op_`, `sess_`, `host_`, `evt_`, `corr_`, `cp_`) (supports FR-001, FR-022, FR-026).
  - **UTC Time Utilities** (`src/rigmate/core/time_utils.py`): Timezone-aware UTC datetime instances and canonical ISO 8601 strings ending in `Z` with naive datetime rejection (supports NFR-007, NFR-009).
  - **Durable JSON / JSONL I/O** (`src/rigmate/storage/json_io.py`): Atomic JSON writes and crash-tolerant JSONL iterator tolerating trailing line corruption while strictly catching middle-stream corruptions (supports FR-009, FR-026, NFR-002, NFR-007).
  - **Generic Event Envelope** (`src/rigmate/core/events.py`): Monotonic sequence, canonical UTC timestamp, and arbitrary payload envelope (supports FR-009, FR-059).
  - **Operation Envelope** (`src/rigmate/core/operations.py`): Strict Blueprint contract enforcing `inspect`, `preview`, `apply` modes, duplicate target rejection, and plan/checkpoint requirements in apply mode (supports FR-022, FR-023, FR-024; execution executor remains incomplete).
  - **Operation Receipt** (`src/rigmate/core/receipts.py`): Contract distinguishing tool success from verified completion, enforcing `verified_at` and `host_revision_after` for completed/recovered states (supports FR-024, FR-026, FR-027, NFR-014).
  - **Generic Capability Registry** (`src/rigmate/core/capabilities.py`): Explicit registry for platform, engine, and provider features with evidence provenance and merge rules (supports FR-013, FR-056).
  - **Disk Budget Preflight** (`src/rigmate/storage/disk_budget.py`): Preflight space calculation incorporating safety margins and estimated checkpoints without file mutations (supports FR-023, FR-026).
  - **Support Bundle Manifest** (`src/rigmate/core/support_bundle.py`): Diagnostic archive metadata model strictly omitting credentials and tokens (supports FR-054, FR-059, NFR-009).
  - **JSON Compatibility Validation** (`src/rigmate/core/json_types.py`): Lightweight recursive validation rejecting NaN, Infinity, bytes, and raw objects (supports NFR-007).
- **Bridge Server & Security**:
  - Localhost-only binding (`127.0.0.1`).
  - Zero-config token discovery via `%LOCALAPPDATA%\RigMate\bridge_state.json`.
  - Full handshake and authenticated endpoints (`/chat`, `/cancel`, `/quota`, `/quota/manual`).
  - Session continuity across turns and real server task cancellation.
- **English-First & i18n Layer**:
  - Canonical English docstrings, comments, server logs, exception classes, and test suites.
  - Centralized i18n layer (`rigmate.core.i18n`) supporting default `en` and localized `vi`.
- **Packaging & Validation**:
  - `scripts/package_addon.py` generates `dist/rigmate_blender_addon_v0.1.0.zip` and verifies file presence, AST syntax, and exclusion of sensitive cache/test files.
