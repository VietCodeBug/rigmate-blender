# RigMate 🦴🤖

**An AI assistant in Blender for users with limited 3D rigging expertise, streamlining the inspection and refinement of generative 3D characters (Hunyuan 3D + Meshy) targeting Godot Engine.**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.0+](https://img.shields.io/badge/Blender-4.0+-orange.svg)](https://www.blender.org/)
[![Status: v0.1.0](https://img.shields.io/badge/Version-v0.1.0-green.svg)]()

---

> [!NOTE]
> **Language & Localization**: English is the canonical language for RigMate source code, developer documentation, logs, and error handling. Vietnamese is supported as an end-user UI locale via our i18n system. (Xem tài liệu tiếng Việt tại [Tài liệu hướng dẫn tại nhà](docs/HOME_SETUP_GUIDE.md)).

---

## 1. Pipeline & Workflow

Typical generative 3D workflows:
1. Generate a character model using **Tencent Hunyuan 3D** (dense mesh topology, ~50,000 vertices).
2. Auto-rig with **Meshy** (basic biped skeleton).
3. Import into **Blender**.
4. **RigMate Assistant**: Inspect unapplied transforms, assess real-time vertex density for game engines, apply heuristic finger bone detection, and prepare clean assets for **Godot Engine**.

> **Design Philosophy:**
> - Non-dogmatic bone structure heuristics: Unmatched bone names do not automatically imply missing fingers.
> - High vertex counts (~50k) are flagged as Godot real-time performance considerations, not topological mesh errors.
> - v0.1 focuses on **safe observation, diagnosis, and conversational guidance**.

---

## 2. Key Highlights in v0.1

- 🔋 **Truthful AI Energy Bar & Quota Tracking**:
  - Differentiates turn token usage, account quota, and plan expiration.
  - Transparent data source tagging: `[Automatic]`, `[Manual Entry]`, or `[DEMO]`.
  - Displays `Automatic quota data is unavailable` when machine-readable endpoints do not exist.
- 💬 **Blender Sidebar Chat Interface**:
  - Located in the 3D Viewport Sidebar (`N` key, RigMate tab).
  - Multi-turn session continuity, local chat persistence, and actual task cancellation.
  - Compact context inspector (`send_selected_only`) without sending massive vertex dumps.
- 🛠️ **FastMCP Server (Model Context Protocol)**:
  - `inspect_scene`: Inspect overall Blender scene state.
  - `inspect_mesh`: Inspect vertex count, modifiers, and vertex groups.
  - `inspect_armature`: Inspect bone hierarchy and transform status.
  - `diagnose_rig`: Automated Godot export readiness analysis.
- 🔒 **Zero-Config Local Security**:
  - Localhost-only binding (`127.0.0.1`) secured by runtime discovery tokens.
  - Atomic JSON writes with automatic recovery from corrupted files and full UTF-8 Unicode support.
- 🌐 **English-First Architecture with i18n Localization**:
  - Canonical English code, comments, docstrings, logs, and internal errors.
  - User-facing UI strings routed through `rigmate.core.i18n.t(key, locale=...)`.

---

## 3. Repository Structure

```text
RigMate/
├── .gitignore
├── LICENSE (GPL-3.0-or-later)
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── docs/
│   ├── ARCHITECTURE.md           # System design & component diagrams
│   ├── DECISIONS.md              # Architectural Decision Records (ADRs)
│   ├── STATUS.md                 # Current environment & verification status
│   ├── HANDOFF.md                # Contributor handoff guide
│   ├── HOME_SETUP_GUIDE.md       # Step-by-step home installation guide
│   └── BLENDER_TESTING_CHECKLIST.md
├── scripts/
│   ├── run_demo.py               # Standalone interactive demo (no Blender needed)
│   └── package_addon.py          # Packages add-on ZIP with automated validation
├── src/
│   └── rigmate/
│       ├── core/                 # Models, analyzers, quota, and i18n
│       ├── storage/              # Atomic local storage & runtime state discovery
│       ├── providers/            # AI Providers (Mock + Antigravity CLI/SDK)
│       ├── bridge/               # FastAPI Bridge server managing sessions & cancellation
│       ├── mcp_server/           # FastMCP Server exposing inspection tools
│       └── blender_addon/        # Blender UI, operators, background client
└── tests/                        # Automated test suite (pytest)
```

---

## 4. Quick Standalone Verification (No Blender Needed)

You can verify all core diagnostic algorithms, session managers, and local storage on any machine without Blender:

### Step 1: Run Automated Tests
```powershell
python -m pytest tests -v
```

### Step 2: Run Standalone Demo
```powershell
python scripts/run_demo.py
```

### Step 3: Package Blender Add-on
```powershell
python scripts/package_addon.py
```
The packaged add-on is generated at: `dist/rigmate_blender_addon_v0.1.0.zip`.

---

## 5. Blender Installation & Setup

For full setup instructions, see [Home Setup Guide](docs/HOME_SETUP_GUIDE.md) and [Blender Testing Checklist](docs/BLENDER_TESTING_CHECKLIST.md).

Summary:
1. Open Blender > `Edit > Preferences > Add-ons > Install...` > Select `dist/rigmate_blender_addon_v0.1.0.zip`.
2. Enable **RigMate - AI Rig Assistant**.
3. Start the Bridge Server in your terminal:
   ```powershell
   python -m rigmate.bridge --host 127.0.0.1 --port 8765
   ```
4. In Blender 3D Viewport, press `N` to open the Sidebar, navigate to the **RigMate** tab, and click **Check Connection**.

---

## 6. Privacy & Data Safety

- Chat history and configuration are stored locally under `%LOCALAPPDATA%\RigMate`.
- **Local storage does not mean offline AI inference**: When you click "Send", the selected context summary and query are transmitted to the configured AI provider.
- Sensitive credentials, auth tokens, and full mesh geometry arrays are never logged or exported.

---

## 7. License

Released under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)** for full compatibility with the Blender ecosystem.
