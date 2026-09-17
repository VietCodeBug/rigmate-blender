"""Automated smoke test verifying packaged Blender add-on dependency boundary.

Verifies:
1. Building add-on ZIP via packaging script.
2. Extracting ZIP to an isolated temporary directory.
3. Simulating an environment where Pydantic, FastAPI, and MCP are completely unavailable.
4. Importing the packaged 'rigmate' root and submodules with a controlled stub 'bpy'.
5. Confirming that all internal imports resolve cleanly without external packages.
6. Confirming that backend server/lifecycle modules are excluded from the ZIP.
"""

import sys
import os
import shutil
import tempfile
import zipfile
import importlib
from pathlib import Path
from unittest.mock import MagicMock
import pytest


def test_packaged_addon_import_resolution():
    """Verify that the packaged ZIP imports cleanly in an environment without Pydantic/FastAPI/MCP."""
    root_dir = Path(__file__).resolve().parent.parent
    dist_dir = root_dir / "dist"
    zip_path = dist_dir / "rigmate_blender_addon_v0.1.0.zip"

    # 1. Ensure root_dir is in sys.path and build package if needed
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from scripts.package_addon import package_blender_addon
    package_blender_addon()

    assert zip_path.exists(), f"Packaged ZIP does not exist at {zip_path}"

    # 2. Extract to temporary directory
    temp_dir = tempfile.mkdtemp(prefix="rigmate_pkg_test_")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        pkg_root = Path(temp_dir)
        assert (pkg_root / "rigmate" / "__init__.py").exists()

        # 3. Setup clean import environment simulating vanilla Blender
        orig_sys_path = list(sys.path)
        orig_sys_modules = dict(sys.modules)

        # Inject stub bpy
        stub_bpy = MagicMock()
        stub_bpy.types.PropertyGroup = object
        stub_bpy.types.Operator = object
        stub_bpy.types.Panel = object
        stub_bpy.props.StringProperty = lambda **kw: ""
        stub_bpy.props.BoolProperty = lambda **kw: False
        stub_bpy.props.FloatProperty = lambda **kw: 0.0
        stub_bpy.props.IntProperty = lambda **kw: 0
        stub_bpy.props.CollectionProperty = lambda **kw: []
        stub_bpy.props.PointerProperty = lambda **kw: None
        stub_bpy.props.EnumProperty = lambda **kw: "en"
        stub_bpy.app.timers.register = MagicMock()
        stub_bpy.utils.register_class = MagicMock()
        stub_bpy.utils.unregister_class = MagicMock()

        sys.modules["bpy"] = stub_bpy
        sys.modules["mathutils"] = MagicMock()

        # STRICT DEPENDENCY BOUNDARY SIMULATION:
        # Explicitly block external Python packages by mapping them to None in sys.modules
        blocked_dependencies = [
            "pydantic",
            "pydantic_core",
            "fastapi",
            "uvicorn",
            "mcp",
            "starlette",
            "httpx",
        ]
        for dep in blocked_dependencies:
            sys.modules[dep] = None

        # Verify simulation: importing any blocked package raises ModuleNotFoundError
        for dep in ["pydantic", "fastapi", "mcp"]:
            with pytest.raises(ModuleNotFoundError):
                importlib.import_module(dep)

        # Remove existing 'rigmate' modules from sys.modules
        for mod_name in list(sys.modules.keys()):
            if mod_name == "rigmate" or mod_name.startswith("rigmate."):
                del sys.modules[mod_name]

        # Insert temp_dir at index 0 so 'import rigmate' resolves strictly to packaged directory
        sys.path.insert(0, temp_dir)

        try:
            # 4. Import root package and verify attributes
            pkg_rigmate = importlib.import_module("rigmate")
            assert hasattr(pkg_rigmate, "bl_info")
            assert pkg_rigmate.bl_info["version"] == (0, 1, 0)
            assert hasattr(pkg_rigmate, "register")
            assert hasattr(pkg_rigmate, "unregister")

            # Call register and unregister to verify property registration
            pkg_rigmate.register()
            pkg_rigmate.unregister()

            # 5. Import all packaged add-on modules directly from packaged tree
            mod_ui = importlib.import_module("rigmate.ui")
            assert hasattr(mod_ui, "VIEW3D_PT_rigmate_main")

            mod_ops = importlib.import_module("rigmate.operators")
            assert hasattr(mod_ops, "RIGMATE_OT_check_connection")
            assert hasattr(mod_ops, "RIGMATE_OT_send_chat")
            assert hasattr(mod_ops, "RIGMATE_OT_diagnose_scene")

            mod_client = importlib.import_module("rigmate.client")
            assert hasattr(mod_client, "RigMateBridgeClient")
            assert hasattr(mod_client, "BridgeConnectionError")
            assert hasattr(mod_client, "BridgeAuthError")

            mod_inspectors = importlib.import_module("rigmate.bpy_inspectors")
            assert hasattr(mod_inspectors, "BpyInspector")

            mod_dto = importlib.import_module("rigmate.dto")
            assert hasattr(mod_dto, "MeshInfo")
            assert hasattr(mod_dto, "ArmatureInfo")
            assert hasattr(mod_dto, "TransformData")

            mod_i18n = importlib.import_module("rigmate.i18n")
            assert hasattr(mod_i18n, "t")
            assert hasattr(mod_i18n, "set_locale")

            mod_analyzer = importlib.import_module("rigmate.analyzer")
            assert hasattr(mod_analyzer, "RigAnalyzer")

            # 6. Verify that heavy server and core lifecycle modules are NOT in packaged ZIP
            for excluded in [
                "rigmate.core.jobs",
                "rigmate.core.job_service",
                "rigmate.core.checkpoints",
                "rigmate.core.plans",
                "rigmate.storage.job_store",
            ]:
                with pytest.raises(ModuleNotFoundError):
                    importlib.import_module(excluded)

            print("\nBLENDER PACKAGE IMPORT: PASS without Pydantic, FastAPI, or MCP")

        finally:
            # Restore environment
            sys.path = orig_sys_path
            for mod_name in list(sys.modules.keys()):
                if mod_name == "rigmate" or mod_name.startswith("rigmate."):
                    del sys.modules[mod_name]
            for dep in blocked_dependencies:
                sys.modules.pop(dep, None)
            sys.modules.update(orig_sys_modules)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
