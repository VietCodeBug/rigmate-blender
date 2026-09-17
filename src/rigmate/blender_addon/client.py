"""Client HTTP giao tiếp từ Blender Add-on tới Bridge chạy nền trên background thread."""

import json
import threading
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, Optional


class RigMateBridgeClient:
    """Client giao tiếp qua HTTP với Bridge Localhost (không làm đứng UI Blender)."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, auth_token: str = ""):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.base_url = f"http://{host}:{port}"
        self.current_thread: Optional[threading.Thread] = None

    def check_health(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Kiểm tra bridge có đang chạy không (đồng bộ nhanh)."""
        url = f"{self.base_url}/health"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
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

            headers = {
                "Content-Type": "application/json",
                "x-rigmate-token": self.auth_token,
            }

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

    def cancel_request(self, session_id: str):
        """Gửi lệnh hủy yêu cầu đang chạy."""
        url = f"{self.base_url}/cancel"
        payload = json.dumps({"session_id": session_id}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-rigmate-token": self.auth_token,
        }
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=3.0):
                pass
        except Exception:
            pass

    def get_quota(self, profile: str = "default") -> Dict[str, Any]:
        """Lấy snapshot quota hiện tại."""
        url = f"{self.base_url}/quota?profile={profile}"
        headers = {"x-rigmate-token": self.auth_token}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {"source": "UNKNOWN", "quota_remaining": None}
