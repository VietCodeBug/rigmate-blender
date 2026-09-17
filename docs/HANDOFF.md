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
│       ├── core/               # Core domain models, analyzers, quota, and i18n (bpy-independent)
│       │   ├── models.py       # Pydantic schemas: SceneInfo, MeshInfo, ArmatureInfo, BoneInfo
│       │   ├── analyzer.py     # Rig diagnosis (Hunyuan 3D + Meshy + Godot readiness)
│       │   ├── quota.py        # QuotaSnapshot, TokenUsage, pure helpers, energy formatting
│       │   ├── i18n.py         # Localization layer: t(), set_locale(), register_locale()
│       │   ├── path_safety.py  # Path containment and traversal protection
│       │   ├── file_hash.py    # Streaming SHA-256 and metadata verification
│       │   ├── schema_version.py # Lightweight semantic schema compatibility parser
│       │   ├── project.py      # ProjectManifest core model (local-only, no cloud account)
│       │   ├── redaction.py    # Recursive data redaction for support bundles
│       │   ├── retry.py        # Bounded exponential backoff policy for idempotent reads
│       │   ├── errors.py       # Centralized machine-readable structured error model
│       │   ├── ids.py          # Collision-safe UUID prefixed identifier generation
│       │   ├── time_utils.py   # Canonical timezone-aware UTC datetime & ISO 8601 formatting
│       │   ├── events.py       # Generic monotonic event envelope
│       │   ├── operations.py   # Blueprint operation envelope contract (inspect/preview/apply)
│       │   ├── receipts.py     # Verified operation execution outcome receipt
│       │   ├── capabilities.py # Generic system, host, engine, and provider capability registry
│       │   ├── support_bundle.py # Support bundle manifest metadata model
│       │   └── json_types.py   # Lightweight JSON compatibility validator
│       ├── storage/            # Local data persistence
│       │   ├── paths.py        # %LOCALAPPDATA%/RigMate
│       │   ├── manager.py      # Atomic writes, corrupt file backup, UTF-8 JSON
│       │   ├── runtime_state.py# bridge_state.json discovery token manager
│       │   ├── retention.py    # Pure checkpoint retention calculator (budget & count bounds)
│       │   ├── json_io.py      # Atomic JSON & crash-tolerant JSONL streaming persistence
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
│           ├── dto.py          # Pure Python standard-library dataclass DTOs (zero Pydantic)
│           ├── i18n.py         # Self-contained add-on localization layer
│           └── analyzer.py     # Self-contained add-on diagnostic analyzer
├── tests/                      # 134 pytest automated unit & integration tests
└── docs/                       # Architectural records, technical guides, checklists
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

### C. Launch Local Bridge Server
```powershell
python -m rigmate.bridge --host 127.0.0.1 --port 8765
```

### D. Package Blender Add-on ZIP
```powershell
python scripts/package_addon.py
```

### E. Run Standalone Demo (No Blender Needed)
```powershell
python scripts/run_demo.py
```

---

## 4. Current Environment State
- **Real Blender Integration**: `REAL BLENDER ADDON LOAD: VERIFIED` (Blender 5.2.1 LTS on Windows 11).
- **Blender Add-on Dependency Boundary**: Pure standard library only (no Pydantic / external wheels inside Blender).
- **Bridge & MCP Server**: Python 3.13 venv with `mcp 2.2.0` fallback compatibility (`FastMCP` / `MCPServer`).
- **Pure Python Tests**: 134/134 tests PASSED.

---

## 5. Next Development Steps
1. Real Blender integration smoke test and hardening pass are complete and verified.
2. Proceed to next roadmap phase according to [docs/ROADMAP.md](ROADMAP.md) (e.g., finger rigging heuristics refinement, weight inspection, or engine export preparations).
3. Ensure any new Blender add-on code strictly adheres to the standard-library boundary (no external imports inside `blender_addon/`).

