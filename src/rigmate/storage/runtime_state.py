"""Local runtime state management (bridge_state.json) for cross-process token discovery."""

import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from rigmate.storage.paths import get_rigmate_app_dir


@dataclass
class BridgeRuntimeState:
    """Runtime state metadata for Bridge Server."""
    auth_token: str
    host: str = "127.0.0.1"
    port: int = 8765
    pid: int = field(default_factory=os.getpid)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "0.1.0"

    def model_dump(self) -> Dict[str, Any]:
        """Dictionary representation for serialization compatibility."""
        return asdict(self)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_stale(self, max_age_hours: float = 12.0) -> bool:
        """Check if runtime state is older than stale threshold."""
        try:
            dt = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt) > timedelta(hours=max_age_hours)
        except Exception:
            return True


class RuntimeStateManager:
    """Safely manage bridge runtime state discovery file in AppData."""

    STATE_FILENAME = "bridge_state.json"

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or get_rigmate_app_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.base_dir / self.STATE_FILENAME

    def save_state(self, state: BridgeRuntimeState):
        """Write runtime state atomically via temporary file."""
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                dir=str(self.base_dir),
                delete=False,
                encoding="utf-8",
                suffix=".tmp",
            ) as f:
                temp_file = Path(f.name)
                json.dump(state.model_dump(), f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            temp_file.replace(self.state_file)
        except Exception as e:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise IOError(f"Failed to write runtime state file: {e}")

    def load_state(self, check_stale: bool = True) -> Optional[BridgeRuntimeState]:
        """Safely load runtime state. Handles corrupted files and stale states."""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = BridgeRuntimeState(**data)
            if check_stale and state.is_stale():
                return None
            return state
        except Exception:
            return None

    def clear_state(self):
        """Clean up runtime state file upon server shutdown."""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except Exception:
                pass
