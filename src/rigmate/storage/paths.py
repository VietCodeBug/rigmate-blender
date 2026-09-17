"""Determine OS-specific application local storage directory path safely."""

import os
import sys
from pathlib import Path


def get_rigmate_app_dir() -> Path:
    """
    Return local application storage directory for RigMate:
    - Windows: %LOCALAPPDATA%/RigMate or %APPDATA%/RigMate
    - Linux: ~/.local/share/rigmate or $XDG_DATA_HOME/rigmate
    - macOS: ~/Library/Application Support/RigMate
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            path = Path(base) / "RigMate"
        else:
            path = Path.home() / ".rigmate"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "RigMate"
    else:
        # Linux / Unix
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            path = Path(xdg) / "rigmate"
        else:
            path = Path.home() / ".local" / "share" / "rigmate"

    path.mkdir(parents=True, exist_ok=True)
    return path
