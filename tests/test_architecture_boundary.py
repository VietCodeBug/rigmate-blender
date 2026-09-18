"""Architecture boundary tests verifying zero dependency leaks and strict contract isolation."""

import ast
import os
import sys
from pathlib import Path
import pytest


SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "rigmate"


def test_no_non_blender_modules_import_blender_addon():
    """
    STRICT BOUNDARY:
    No runtime file outside `src/rigmate/blender_addon/` may import `rigmate.blender_addon`.
    Inspects: core/, storage/, providers/, bridge/, mcp_server/, testing/, contracts/, analysis/, localization/.
    """
    forbidden_import_targets = {
        "rigmate.blender_addon",
        "blender_addon",
    }

    violations = []

    for root, dirs, files in os.walk(SRC_DIR):
        root_path = Path(root)
        # Skip the blender_addon package itself
        if "blender_addon" in root_path.parts:
            continue
        if "__pycache__" in root_path.parts:
            continue

        for f in files:
            if not f.endswith(".py"):
                continue
            py_file = root_path / f
            code = py_file.read_text(encoding="utf-8")
            tree = ast.parse(code, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for target in forbidden_import_targets:
                            if alias.name == target or alias.name.startswith(f"{target}."):
                                violations.append((py_file, node.lineno, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for target in forbidden_import_targets:
                        if mod == target or mod.startswith(f"{target}."):
                            violations.append((py_file, node.lineno, mod))

    assert not violations, f"Detected architectural dependency violations (Core/Storage -> Blender):\n{violations}"


def test_neutral_contracts_pure_stdlib_isolation():
    """
    `rigmate.contracts` must import cleanly even when Pydantic, bpy, FastAPI, and MCP are unavailable.
    """
    # Create an isolated environment simulation
    code = """
import sys

# Mask forbidden external libraries
for blocked in ['pydantic', 'bpy', 'fastapi', 'mcp', 'httpx', 'uvicorn']:
    sys.modules[blocked] = None

# Import neutral contracts
import rigmate.contracts
import rigmate.contracts.dto
import rigmate.contracts.host
import rigmate.contracts.hashing
import rigmate.analysis
import rigmate.analysis.rig
import rigmate.localization
import rigmate.localization.engine

# Verify contracts did not load core, storage, or blender_addon
assert 'rigmate.core' not in sys.modules, "Contracts must not import core"
assert 'rigmate.storage' not in sys.modules, "Contracts must not import storage"
assert 'rigmate.blender_addon' not in sys.modules, "Contracts must not import blender_addon"

print("CONTRACTS_ISOLATION_OK")
"""
    proc = subprocess_run_python(code)
    assert proc.returncode == 0, f"Contracts isolation check failed: {proc.stderr}"
    assert "CONTRACTS_ISOLATION_OK" in proc.stdout


def subprocess_run_python(code: str):
    import subprocess
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
