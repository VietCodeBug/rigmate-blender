# Engineer Handoff Document

This document enables any developer, contributor, or AI agent to understand and take over development of **RigMate** without relying on previous chat history.

---

## 1. Workspace & Repository Metadata
- **Workspace Path**: `D:\MCP_Blender\rigmate-blender`
- **Git Remote**: `https://github.com/VietCodeBug/rigmate-blender.git`
- **Primary Branch**: `main`
- **License**: `LICENSE` (GPL-3.0-or-later)
- **Canonical Technical Language**: English (Internal code, docstrings, comments, logs, errors, tests, and contributor docs).
- **Supported Localization**: English (`en` - source/default), Vietnamese (`vi`).

---

## 2. Module Map

```text
D:\MCP_Blender\rigmate-blender\
├── pyproject.toml              # Project dependencies (fastapi, uvicorn, pydantic, mcp, pytest...)
├── .gitignore                  # Excludes local storage, runtime tokens, cache, dist
├── dist/                       # Output directory for packaged add-on ZIP
│   └── rigmate_blender_addon_v0.1.0.zip
├── scripts/
│   ├── run_demo.py             # 3-step interactive demo running without Blender
│   └── package_addon.py        # Bundles add-on ZIP with automated AST/integrity checks
├── src/
│   └── rigmate/
│       ├── contracts/          # Pure Python standard-library neutral contracts (zero external dependencies)
│       │   ├── dto.py          # Canonical DTOs: MeshInfo, ArmatureInfo, BoneInfo, RigDiagnosticReport
│       │   ├── host.py         # HostAdapter protocol, HostOperationRequest, HostOperationStatus
│       │   └── hashing.py      # Canonical SHA-256 operation request hashing
│       ├── analysis/           # Pure Python standard-library deterministic rig analysis
│       │   └── rig.py          # RigAnalyzer, finger/side heuristics (Hunyuan 3D + Meshy + Godot readiness)
│       ├── localization/       # Pure Python standard-library internationalization
│       │   └── engine.py       # Translation engine (English canonical/default, Vietnamese supported)
│       ├── core/               # External Core domain models, jobs, recovery, and lifecycle
│       │   ├── models.py       # Pydantic domain models
│       │   ├── dto.py          # Compatibility re-export shim -> rigmate.contracts.dto
│       │   ├── analyzer.py     # Compatibility re-export shim -> rigmate.analysis.rig
│       │   ├── i18n.py         # Compatibility re-export shim -> rigmate.localization.engine
│       │   ├── host_protocol.py# Compatibility re-exports and host_request_from_operation() adapter
│       │   ├── jobs.py         # JobRecord, JobStatus state machine
│       │   ├── job_service.py  # Orchestrates lifecycle, writer locks, and crash recovery
│       │   ├── recovery.py     # Journal reconciliation and recovery scanner
│       │   ├── checkpoints.py  # Checkpoint pre-mutation snapshot validation
│       │   ├── operations.py   # OperationEnvelope Pydantic models
│       │   ├── receipts.py     # OperationReceipt, ReceiptStatus, ReceiptError
│       │   ├── lock.py         # Document single-writer locks
│       │   └── timeline.py     # Event journal timeline aggregation
│       ├── testing/            # Headless test support fakes
│       │   └── durable_host.py # Filesystem-backed DurableFakeHost for crash & restart tests
│       ├── storage/            # Local data persistence
│       │   ├── paths.py        # %LOCALAPPDATA%/RigMate
│       │   ├── manager.py      # Atomic writes, corrupt file backup, UTF-8 JSON
│       │   ├── runtime_state.py# bridge_state.json discovery token manager
│       │   ├── retention.py    # Pure checkpoint retention calculator (budget & count bounds)
│       │   ├── json_io.py      # Atomic JSON & crash-tolerant JSONL streaming persistence
│       │   ├── checkpoints.py  # Content-addressed snapshot engine (.rigmate/blobs/)
│       │   ├── idempotency.py  # Durable SHA-256 operation idempotency registry
│       │   ├── job_store.py    # Multi-entity job directory and journal store
│       │   └── disk_budget.py  # Preflight disk space evaluation with safety margin
│       ├── providers/          # AI Provider adapters
│       │   ├── base.py         # Abstract interfaces BaseAIProvider, BaseQuotaProvider
│       │   ├── capabilities.py # Provider capability matrix & evidence audit trail
│       │   ├── mock_provider.py# MockProvider tailored for Hunyuan/Meshy scenarios
│       │   └── antigravity_provider.py # Antigravity CLI/SDK adapter with UNVERIFIED_ENV fallback
│       ├── bridge/             # Localhost Bridge Server (FastAPI)
│       │   ├── __main__.py     # Entrypoint: python -m rigmate.bridge [--host] [--port]
│       │   ├── server.py       # Endpoints: /health, /chat, /cancel, /quota, /quota/manual
│       │   └── session.py      # Session continuity and task cancellation manager
│       ├── mcp_server/         # Model Context Protocol server (FastMCP)
│       │   ├── server.py       # Stdio MCP Server exposing tools
│       │   └── tools.py        # inspect_scene, inspect_mesh, inspect_armature, diagnose_rig
│       └── blender_addon/      # Blender Add-on UI & Operators (Zero External Dependencies)
│           ├── __init__.py     # bl_info, property definitions, registration
│           ├── ui.py           # 3D Viewport sidebar panel (N-Panel), energy bar, chat
│           ├── operators.py    # Operators for connection, chat, cancellation, quota dialog
│           ├── client.py       # Asynchronous HTTP background client with zero-dep token discovery
│           ├── bpy_inspectors.py # Context inspection converting bpy data to DTOs
│           ├── dto.py          # Compatibility re-export shim -> rigmate.contracts.dto
│           ├── i18n.py         # Compatibility re-export shim -> rigmate.localization.engine
│           └── analyzer.py     # Compatibility re-export shim -> rigmate.analysis.rig
├── tests/                      # 166 pytest automated unit & integration tests
│   ├── helpers/                # Subprocess restart worker for multi-process crash tests
│   ├── fixtures/characters/    # Compact neutral character inspection fixtures
│   ├── test_architecture_boundary.py # AST dependency boundary & contract isolation tests
│   └── test_process_restart_subprocess.py # Child process OS restart proofs
└── docs/                       # Architectural records, technical guides, checklists
    └── modules/
        └── mesh_preparation.md # Canonical specification: Mesh Preparation ("Kiểm tra & sửa lưới")
```

---

## 3. Essential Commands

### A. Environment Setup
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[bridge,dev]"
```

### B. Run Automated Tests
```powershell
python -m pytest tests -v
```

### C. Run Integrity & Packaging Checks
```powershell
python scripts/check_repo_integrity.py
python scripts/package_addon.py
```

### D. Launch Local Bridge Server
```powershell
python -m rigmate.bridge --host 127.0.0.1 --port 8765
```

### E. Run Standalone Demo (No Blender Needed)
```powershell
python scripts/run_demo.py
```

---

## 4. Current Environment State
- **Core Host Protocol**: `VERIFIED` (neutral protocol, read-only inspect/prepare, zero Pydantic).
- **Neutral Contract Layer**: `VERIFIED` (pure standard library, zero Core -> Blender dependency).
- **Durable Fake Host**: `VERIFIED` (filesystem-backed host state, independent persistence).
- **Fresh Object Reconstruction**: `VERIFIED` (objects destroyed and recreated in RAM from disk).
- **Real Python Process-Restart ACK-Loss**: `VERIFIED` (multi-process subprocess proof: Phase A crashes with exit 42, Phase B recovers in fresh PID, 0 duplicate apply calls, mutation count strictly 1).
- **Mesh Preparation Spec**: `COMPLETE` (canonical spec at `docs/modules/mesh_preparation.md`).
- **Headless Contract Design**: `COMPLETE` (structured tool envelopes, region references, finding schemas).
- **Real Blender Host Adapter**: `UNVERIFIED` (implementation reserved for machine with physical Blender).
- **Real Blender Mesh Inspection**: `UNVERIFIED` (BMesh algorithm specified; pending physical Blender test).
- **Real Blender Mesh Repair**: `NOT IMPLEMENTED` (intentionally not implemented; reserved for Phase B).
- **Real UV/Weight/Shape-Key Preservation**: `UNVERIFIED` (preservation matrix specified; pending physical Blender test).
- **Real Blender Mutation**: `NOT PERFORMED` (intentionally not performed; machine has no physical Blender).
- **Real Blender ACK-Loss**: `NOT PERFORMED` (reserved for real Blender runtime experiments).
- **Real Godot Import Validation**: `NOT PERFORMED` (contextual budget advisory specified; pending real Godot verification).
- **Auto Retopology Backend**: `NOT SELECTED / RESEARCH STATUS` (Phase E research).
- **Real Godot Host**: `NOT PERFORMED` (future milestone).
- **Pure Python Tests**: **166/166 tests PASSED**.

---

## 5. Work Reserved For Home Blender Machine
The following tasks genuinely require a physical Blender installation and should be completed when working on the home machine with Blender:
1. Implement `RealBlenderHostAdapter` in `src/rigmate/blender_addon/` conforming to `HostAdapter`.
2. Map `inspect_document()` to live `bpy` data (meshes, armatures, bone collections).
3. Implement one tiny, reversible, typed mutation tool in Blender (e.g. `object.rename`).
4. Connect real Blender host status persistence to a durable local state file before acknowledging IPC.
5. Run the full closed-loop lifecycle (checkpoint -> apply -> verify) against a live Blender session.
6. Conduct real ACK-loss and process crash experiments against Blender.

---

## 6. Next Immediate Implementation Slice (Phase A: Read-Only Mesh Inspection)
The very next implementation task should be **strictly read-only** and can be developed and verified headlessly right now:
1. **Contract DTOs**: Define `MeshStatistics`, `MeshRegionReference`, `MeshFinding`, and `MeshInspectionReport` in `src/rigmate/contracts/dto.py`.
2. **Analysis Module**: Implement pure Python inspection rules in `src/rigmate/analysis/mesh.py` (poly/tri counts, loose geometry, near-duplicate threshold calculation, unweighted vertices, inverted normals).
3. **Headless Fixture Tests**: Add unit tests in `tests/test_mesh_inspection.py` verifying detection against JSON character fixtures (`clean_static_mesh.json`, `non_manifold_region.json`, `unweighted_vertices.json`).
4. **Tool Contract**: Add read-only `mesh.inspect` tool definition to MCP server.
5. **Blender Extraction Stub**: Implement BMesh reader stub in `src/rigmate/blender_addon/bpy_inspectors.py`.
*(Note: Do NOT implement geometry mutation or retopology algorithms until Phase A inspection is 100% verified).*



