# Contributing Guidelines for RigMate

Thank you for your interest in contributing to **RigMate**!

RigMate aims to help content creators, indie game developers, and artists with limited 3D rigging expertise turn generative 3D models into game-ready animated assets.

---

## 1. Technical Standards & Guidelines

- **License**: All source contributions are distributed under **GPL-3.0-or-later**.
- **English-First Canonical Language**:
  - Source code, comments, docstrings, variable/function names, exceptions, error codes, logs, and developer documentation must be written in **standard English**.
  - Internal logic must never hardcode localized strings or use translated text as identifiers.
- **Localization (i18n)**:
  - User-facing UI labels, dialogs, and reports must be routed through `rigmate.core.i18n.t(key, locale=...)`.
  - English (`en`) is the default and fallback locale. Additional translations (e.g. Vietnamese `vi`) are registered in `rigmate.core.i18n`.
- **Zero Bpy In Core**: Never import `bpy` into `rigmate.core`, `rigmate.storage`, or `rigmate.providers`. Core diagnostic logic must run completely standalone outside Blender.
- **Mandatory Testing**: All new features and bug fixes must include unit tests under `tests/`.

---

## 2. Development Workflow

1. **Fork** the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Set up the development environment:
   ```bash
   pip install -e ".[bridge,dev]"
   ```
3. Run the automated test suite:
   ```bash
   python -m pytest tests -v
   ```
4. Verify packaging and syntax checks:
   ```bash
   python scripts/package_addon.py
   ```
5. Follow Conventional Commits:
   - `feat: add bone symmetry analysis heuristic`
   - `fix: handle zero-total quota percentage calculation`
   - `docs: update MCP tool documentation`
6. Open a **Pull Request** detailing changes and verification steps.

---

## 3. Reporting Issues

When submitting an issue on GitHub, please include:
- Blender version (if applicable).
- Source model generator (e.g., Tencent Hunyuan 3D, Meshy, Tripo3D).
- Steps to reproduce and traceback logs (all logs are in English).
