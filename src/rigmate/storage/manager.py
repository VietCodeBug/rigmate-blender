"""Local persistent storage management: Atomic writes, corrupt recovery, export and clear data."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from rigmate.core.quota import QuotaSnapshot
from rigmate.storage.paths import get_rigmate_app_dir


class StorageManager:
    """
    Local JSON storage manager:
    - Atomic write using temporary files to prevent corruption during unexpected shutdowns
    - Automatic backup and recovery upon encountering corrupted JSON files (.corrupt.bak)
    - Full UTF-8 support (ensure_ascii=False)
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or get_rigmate_app_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.base_dir / "chat_history.json"
        self.settings_file = self.base_dir / "user_settings.json"
        self.quota_file = self.base_dir / "quota_snapshots.json"

    def _atomic_write_json(self, file_path: Path, data: Any):
        """Write JSON data atomically via a temporary file in the same directory."""
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
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            temp_file.replace(file_path)
        except Exception as e:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise IOError(f"Failed to write data atomically to {file_path}: {e}")

    def _safe_read_json(self, file_path: Path, default_value: Any) -> Any:
        """Safely read JSON file. If corrupted, create a .corrupt.bak backup and return default."""
        if not file_path.exists():
            return default_value

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            corrupt_backup = file_path.with_suffix(".corrupt.bak")
            try:
                shutil.copy2(file_path, corrupt_backup)
            except Exception:
                pass
            return default_value

    # --- Chat History Management ---

    def save_chat_history(self, session_id: str, messages: List[Dict[str, Any]]):
        """Save conversation history for a given session_id."""
        history = self._safe_read_json(self.history_file, default_value={})
        history[session_id] = messages
        self._atomic_write_json(self.history_file, history)

    def load_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Load conversation history for a given session_id."""
        history = self._safe_read_json(self.history_file, default_value={})
        return history.get(session_id, [])

    def list_chat_sessions(self) -> List[str]:
        """List all saved chat session IDs."""
        history = self._safe_read_json(self.history_file, default_value={})
        return list(history.keys())

    def clear_all_history(self):
        """Clear all chat history."""
        self._atomic_write_json(self.history_file, {})

    # --- Quota Snapshot Management ---

    def save_quota_snapshot(self, snapshot: QuotaSnapshot):
        """
        Save quota snapshot tied to profile, provider and model.
        Prevents cross-account contamination when switching users.
        """
        data = self._safe_read_json(self.quota_file, default_value={})
        key = f"{snapshot.account_profile}:{snapshot.provider_name}:{snapshot.model_name}"
        data[key] = snapshot.model_dump()
        self._atomic_write_json(self.quota_file, data)

    def load_quota_snapshot(
        self,
        account_profile: str = "default",
        provider_name: str = "Unknown",
        model_name: str = "Unknown",
    ) -> Optional[QuotaSnapshot]:
        """Load quota snapshot for a specific profile."""
        data = self._safe_read_json(self.quota_file, default_value={})
        key = f"{account_profile}:{provider_name}:{model_name}"
        item = data.get(key)
        if item:
            try:
                return QuotaSnapshot(**item)
            except Exception:
                return None
        return None

    def invalidate_snapshots_for_profile(self, account_profile: str):
        """Invalidate or remove snapshots belonging to a profile upon sign-out."""
        data = self._safe_read_json(self.quota_file, default_value={})
        keys_to_remove = [k for k in data.keys() if k.startswith(f"{account_profile}:")]
        for k in keys_to_remove:
            del data[k]
        self._atomic_write_json(self.quota_file, data)

    # --- Data Export & Backup ---

    def export_all_data(self, target_export_path: Path):
        """Export all settings, history, and quota snapshots to a single JSON file."""
        export_data = {
            "chat_history": self._safe_read_json(self.history_file, {}),
            "settings": self._safe_read_json(self.settings_file, {}),
            "quota_snapshots": self._safe_read_json(self.quota_file, {}),
        }
        with open(target_export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
