"""Automated smoke test verifying packaged add-on import resolution.

Verifies:
1. Building add-on ZIP via packaging script.
2. Extracting ZIP to an isolated temporary directory.
3. Importing the packaged 'rigmate' root modules and subpackages with a controlled stub 'bpy'.
4. Confirming that all relative and absolute internal imports resolve cleanly.
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
    """Verify that the packaged ZIP structure imports cleanly without unresolved paths."""
    root_dir = Path(__file__).resolve().parent.parent
    dist_dir = root_dir / "dist"
    zip_path = dist_dir / "rigmate_blender_addon_v0.1.0.zip"

    # 1. Build package if not already built
    if not zip_path.exists():
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

        # 3. Setup clean import environment with stubbed bpy
        # Preserve original sys.path and sys.modules
        orig_sys_path = list(sys.path)
        orig_sys_modules = dict(sys.modules)

        # Ensure stub bpy is injected only if real bpy is absent
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

        # Insert temp_dir at index 0 so 'import rigmate' resolves to packaged directory
        # Remove existing 'rigmate' modules from sys.modules to force fresh import from temp_dir
        for mod_name in list(sys.modules.keys()):
            if mod_name == "rigmate" or mod_name.startswith("rigmate."):
                del sys.modules[mod_name]

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

            # 5. Import all add-on modules directly from packaged tree
            mod_ui = importlib.import_module("rigmate.ui")
            assert hasattr(mod_ui, "VIEW3D_PT_rigmate_main")

            mod_ops = importlib.import_module("rigmate.operators")
            assert hasattr(mod_ops, "RIGMATE_OT_check_connection")
            assert hasattr(mod_ops, "RIGMATE_OT_send_chat")

            mod_client = importlib.import_module("rigmate.client")
            assert hasattr(mod_client, "RigMateBridgeClient")
            assert hasattr(mod_client, "BridgeConnectionError")
            assert hasattr(mod_client, "BridgeAuthError")

            mod_inspectors = importlib.import_module("rigmate.bpy_inspectors")
            assert hasattr(mod_inspectors, "BpyInspector")

            mod_core = importlib.import_module("rigmate.core")
            mod_core_i18n = importlib.import_module("rigmate.core.i18n")
            assert hasattr(mod_core_i18n, "t")
            assert hasattr(mod_core_i18n, "set_locale")

            mod_core_models = importlib.import_module("rigmate.core.models")
            assert hasattr(mod_core_models, "SceneInfo")

            mod_core_analyzer = importlib.import_module("rigmate.core.analyzer")
            assert hasattr(mod_core_analyzer, "RigAnalyzer")

            mod_core_quota = importlib.import_module("rigmate.core.quota")
            assert hasattr(mod_core_quota, "QuotaSnapshot")
            assert hasattr(mod_core_quota, "TokenUsage")

            mod_storage = importlib.import_module("rigmate.storage")
            mod_storage_mgr = importlib.import_module("rigmate.storage.manager")
            assert hasattr(mod_storage_mgr, "StorageManager")

            mod_storage_state = importlib.import_module("rigmate.storage.runtime_state")
            assert hasattr(mod_storage_state, "RuntimeStateManager")

            print("\nPACKAGED PYTHON IMPORT TEST: PASSED")
            print("REAL BLENDER TEST: NOT PERFORMED")

        finally:
            # Restore environment
            sys.path = orig_sys_path
            # Purge temp rigmate modules
            for mod_name in list(sys.modules.keys()):
                if mod_name == "rigmate" or mod_name.startswith("rigmate."):
                    del sys.modules[mod_name]
            # Restore original modules
            sys.modules.update(orig_sys_modules)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
