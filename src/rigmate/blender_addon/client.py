"""Client HTTP giao tiếp từ Blender Add-on tới Bridge chạy nền trên background thread."""

import json
import threading
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, Optional


from rigmate.storage.runtime_state import RuntimeStateManager


class RigMateBridgeClient:
    """Client giao tiếp qua HTTP với Bridge Localhost (không làm đứng UI Blender)."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, auth_token: str = ""):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.base_url = f"http://{host}:{port}"
        self.current_thread: Optional[threading.Thread] = None
        self.state_manager = RuntimeStateManager()

        # Tự động phát hiện token nếu chưa được cung cấp
        if not self.auth_token:
            self.discover_token()

    def discover_token(self) -> bool:
        """Tự động tìm kiếm runtime token từ AppData do Bridge ghi ra."""
        state = self.state_manager.load_state(check_stale=True)
        if state and state.auth_token:
            self.auth_token = state.auth_token
            self.host = state.host
            self.port = state.port
            self.base_url = f"http://{self.host}:{self.port}"
            return True
        return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Tạo headers kèm token. Nếu chưa có token, thử discover lại một lần."""
        if not self.auth_token:
            self.discover_token()
        return {
            "Content-Type": "application/json",
            "x-rigmate-token": self.auth_token,
        }

    def check_health(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Kiểm tra bridge có đang chạy không (đồng bộ nhanh)."""
        # Thử refresh token khi kiểm tra kết nối
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
        on_error: Callable[[str], None],
        timeout: float = 40.0,
    ):
        """Gửi yêu cầu trò chuyện bất đồng bộ trong thread riêng để không freeze Blender UI."""
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
                on_error(f"Lỗi HTTP {e.code}: {e.reason}")
            except urllib.error.URLError as e:
                on_error(f"Không thể kết nối Bridge tại {self.base_url}: {e.reason}")
            except Exception as e:
                on_error(f"Lỗi gửi yêu cầu: {e}")

        self.current_thread = threading.Thread(target=_worker, daemon=True)
        self.current_thread.start()

    def cancel_request(self, session_id: str) -> bool:
        """Gửi lệnh hủy yêu cầu đang chạy."""
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
        """Lấy snapshot quota hiện tại."""
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
        """Gửi snapshot hạn mức thủ công lên Bridge và persist vào storage."""
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
