"""HTTP client communicating with RigMate Bridge asynchronously on background threads."""

import json
import threading
import urllib.request
import urllib.error
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional


@dataclass
class BridgeState:
    auth_token: str
    host: str = "127.0.0.1"
    port: int = 8765


class LocalRuntimeStateManager:
    """Blender-safe bridge state loader using standard library only."""

    @staticmethod
    def _get_app_dir() -> Path:
        if sys.platform.startswith("win"):
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                return Path(base) / "RigMate"
            return Path.home() / ".rigmate"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "RigMate"
        else:
            xdg = os.environ.get("XDG_DATA_HOME")
            if xdg:
                return Path(xdg) / "rigmate"
            return Path.home() / ".local" / "share" / "rigmate"

    def load_state(self, check_stale: bool = True) -> Optional[BridgeState]:
        try:
            state_file = self._get_app_dir() / "bridge_state.json"
            if not state_file.is_file():
                return None
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if check_stale and "started_at" in data:
                dt = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - dt) > timedelta(hours=12.0):
                    return None
            return BridgeState(
                auth_token=data.get("auth_token", ""),
                host=data.get("host", "127.0.0.1"),
                port=int(data.get("port", 8765)),
            )
        except Exception:
            return None


class BridgeClientError(Exception):
    """Base exception for RigMate bridge communication failures."""
    error_code: str = "bridge.error"

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class BridgeConnectionError(BridgeClientError):
    """Bridge is offline, unreachable, or refused connection."""
    error_code: str = "bridge.connection_failed"


class BridgeAuthError(BridgeClientError):
    """Bridge authentication failed or token is missing/invalid."""
    error_code: str = "bridge.auth_failed"


class BridgeTimeoutError(BridgeClientError):
    """Bridge request timed out."""
    error_code: str = "bridge.timeout"


class RigMateBridgeClient:
    """HTTP Client communicating with local Bridge without freezing Blender main thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, auth_token: str = ""):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.base_url = f"http://{host}:{port}"
        self.current_thread: Optional[threading.Thread] = None
        self.state_manager = LocalRuntimeStateManager()

        if not self.auth_token:
            self.discover_token()

    def discover_token(self) -> bool:
        """Discover runtime auth token from local AppData written by Bridge."""
        state = self.state_manager.load_state(check_stale=True)
        if state and state.auth_token:
            self.auth_token = state.auth_token
            self.host = state.host
            self.port = state.port
            self.base_url = f"http://{self.host}:{self.port}"
            return True
        return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Construct HTTP headers with token; attempts rediscovery if token is missing."""
        if not self.auth_token:
            self.discover_token()
        return {
            "Content-Type": "application/json",
            "x-rigmate-token": self.auth_token,
        }

    def check_health(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Fast synchronous health check."""
        self.discover_token()
        url = f"{self.base_url}/health"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    data["token_discovered"] = bool(self.auth_token)
                    return data
        except Exception:
            pass
        return {"status": "offline"}

    def send_chat_async(
        self,
        message: str,
        session_id: Optional[str],
        context_data: Optional[Dict[str, Any]],
        on_success: Callable[[Dict[str, Any]], None],
        on_error: Callable[[str, str], None],
        timeout: float = 40.0,
    ):
        """Send chat request asynchronously in a daemon thread to avoid blocking UI."""
        def _worker():
            url = f"{self.base_url}/chat"
            payload = json.dumps({
                "session_id": session_id,
                "message": message,
                "context_data": context_data,
            }).encode("utf-8")

            headers = self.get_auth_headers()

            try:
                req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    on_success(data)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    on_error("bridge.auth_failed", f"HTTP {e.code}: Authentication failed")
                else:
                    on_error("bridge.http_error", f"HTTP {e.code}: {e.reason}")
            except urllib.error.URLError as e:
                on_error("bridge.connection_failed", f"Cannot connect to Bridge at {self.base_url}: {e.reason}")
            except TimeoutError:
                on_error("bridge.timeout", f"Request to Bridge timed out after {timeout}s")
            except Exception as e:
                on_error("bridge.error", f"Request error: {e}")

        self.current_thread = threading.Thread(target=_worker, daemon=True)
        self.current_thread.start()

    def cancel_request(self, session_id: str) -> bool:
        """Send cancellation signal for active request."""
        url = f"{self.base_url}/cancel"
        payload = json.dumps({"session_id": session_id}).encode("utf-8")
        headers = self.get_auth_headers()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return bool(data.get("cancelled", False))
        except Exception:
            return False

    def get_quota(self, profile: str = "default") -> Dict[str, Any]:
        """Fetch active quota snapshot from Bridge."""
        url = f"{self.base_url}/quota?profile={profile}"
        headers = self.get_auth_headers()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {"source": "UNKNOWN", "quota_remaining": None}

    def update_manual_quota(
        self,
        provider_name: str,
        model_name: str,
        quota_remaining: float,
        quota_total: Optional[float] = None,
        quota_unit: str = "requests",
        account_profile: str = "default",
        plan_expiration: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post manual quota snapshot to Bridge and persist to local storage."""
        url = f"{self.base_url}/quota/manual"
        payload = json.dumps({
            "provider_name": provider_name,
            "model_name": model_name,
            "account_profile": account_profile,
            "quota_remaining": quota_remaining,
            "quota_total": quota_total,
            "quota_unit": quota_unit,
            "plan_expiration": plan_expiration,
        }).encode("utf-8")
        headers = self.get_auth_headers()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": "error", "message": str(e)}
