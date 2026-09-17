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
