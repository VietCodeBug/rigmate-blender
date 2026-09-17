# Engineer Handoff Document

This document enables any developer, contributor, or AI agent to understand and take over development of **RigMate** without relying on previous chat history.

---

## 1. Workspace & Repository Metadata
- **Workspace Path**: `D:\Ark_3\RigMate`
- **Git Remote**: `https://github.com/VietCodeBug/rigmate-blender.git`
- **Primary Branch**: `main`
- **License**: `LICENSE` (GPL-3.0-or-later)
- **Canonical Technical Language**: English (Internal code, docstrings, comments, logs, errors, tests, and contributor docs).
- **Supported Localization**: English (`en` - source/default), Vietnamese (`vi`).

---

## 2. Module Map

```text
D:\Ark_3\RigMate\
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
│       │   ├── quota.py        # QuotaSnapshot, TokenUsage, energy formatting
│       │   └── i18n.py         # Localization layer: t(), set_locale(), register_locale()
│       ├── storage/            # Local data persistence
│       │   ├── paths.py        # %LOCALAPPDATA%/RigMate
│       │   ├── manager.py      # Atomic writes, corrupt file backup, UTF-8 JSON
│       │   └── runtime_state.py# bridge_state.json discovery token manager
│       ├── providers/          # AI Provider adapters
│       │   ├── base.py         # Abstract interfaces BaseAIProvider, BaseQuotaProvider
│       │   ├── mock_provider.py# MockProvider tailored for Hunyuan/Meshy scenarios
│       │   └── antigravity_provider.py # Antigravity CLI/SDK adapter with UNVERIFIED_ENV fallback
│       ├── bridge/             # Localhost Bridge Server (FastAPI)
│       │   ├── __main__.py     # Entrypoint: python -m rigmate.bridge [--host] [--port]
│       │   ├── server.py       # Endpoints: /health, /chat, /cancel, /quota, /quota/manual
│       │   └── session.py      # Session continuity and task cancellation manager
│       ├── mcp_server/         # Model Context Protocol server (FastMCP)
│       │   ├── server.py       # Stdio MCP Server exposing tools
│       │   └── tools.py        # inspect_scene, inspect_mesh, inspect_armature, diagnose_rig
│       └── blender_addon/      # Blender Add-on UI & Operators
│           ├── __init__.py     # bl_info, property definitions, registration
│           ├── ui.py           # 3D Viewport sidebar panel (N-Panel), energy bar, chat
│           ├── operators.py    # Operators for connection, chat, cancellation, quota dialog
│           ├── client.py       # Asynchronous HTTP background client with token discovery
│           └── bpy_inspectors.py # Context inspection converting bpy data to core schemas
├── tests/                      # 32 pytest automated tests
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
- **Blender on Test Machine**: `REAL BLENDER TEST: NOT PERFORMED`.
- **Antigravity CLI on Test Machine**: `UNVERIFIED_ENV` (neither `agy` CLI nor SDK detected).
- **Pure Python Tests**: 32/32 tests PASSED.

---

## 5. Next Steps for Real Blender Verification
1. Install `dist/rigmate_blender_addon_v0.1.0.zip` via Blender `Edit > Preferences > Add-ons > Install...`.
2. Start the bridge: `python -m rigmate.bridge`.
3. Open the **RigMate** tab in the 3D View Sidebar (`N` key).
4. Follow the testing steps in [docs/BLENDER_TESTING_CHECKLIST.md](BLENDER_TESTING_CHECKLIST.md).
