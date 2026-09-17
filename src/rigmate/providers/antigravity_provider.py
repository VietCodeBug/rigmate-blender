"""Antigravity CLI / Python SDK Adapter với cơ chế phát hiện và xử lý lỗi môi trường."""

import asyncio
import os
import shutil
import subprocess
from typing import AsyncGenerator, List, Optional
from rigmate.core.quota import QuotaSnapshot, TokenUsage
from rigmate.providers.base import BaseAIProvider, BaseQuotaProvider, ChatMessage, ProviderResponse


class AntigravityProvider(BaseAIProvider, BaseQuotaProvider):
    """
    Adapter tương tác với Antigravity CLI (`agy`) hoặc Antigravity Python SDK.
    - Không suy đoán hoặc bịa tham số nếu CLI chưa sẵn sàng.
    - Đánh dấu rõ trạng thái `UNVERIFIED_ENV` khi chạy trên máy chưa có CLI hoặc chưa đăng nhập.
    - Tuân thủ nguyên tắc: Không tự trích xuất cookie/token nội bộ, không tự chuyển sang API tính phí.
    """

    def __init__(self, model: str = "gemini-3.8-flash"):
        self._model = model
        self.cli_path = self._detect_cli_path()
        self.sdk_available = self._detect_sdk()

    @property
    def provider_id(self) -> str:
        return "antigravity"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Kiểm tra xem môi trường hiện tại có thể gọi được CLI hoặc SDK không."""
        return bool(self.cli_path or self.sdk_available)

    def _detect_cli_path(self) -> Optional[str]:
        """Tìm binary `agy` trong PATH hệ thống."""
        return shutil.which("agy")

    def _detect_sdk(self) -> bool:
        """Kiểm tra xem google.antigravity SDK có được cài trong môi trường Python này không."""
        try:
            import google.antigravity  # type: ignore
            return True
        except ImportError:
            return False

    async def generate_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
        timeout_seconds: float = 30.0,
    ) -> ProviderResponse:
        if not self.is_available():
            # Máy chưa có CLI hoặc SDK
            return ProviderResponse(
                text=(
                    "[UNVERIFIED_ENV] Chưa phát hiện Antigravity CLI ('agy') hoặc Python SDK ('google.antigravity') "
                    "trong môi trường hiện tại. Vui lòng kiểm tra hướng dẫn cài đặt tại nhà (HOME_SETUP_GUIDE.md) "
                    "hoặc chuyển sang chế độ 'Mock Provider' trong cài đặt RigMate."
                ),
                token_usage=TokenUsage.create(0, 0),
                suggested_actions=["Chuyển sang Mock Provider", "Mở Hướng dẫn Cài đặt"],
                raw_metadata={"status": "UNVERIFIED_ENV", "session_id": session_id},
            )

        # Lấy prompt của user gần nhất
        last_prompt = messages[-1].content if messages else ""

        # Nếu có SDK
        if self.sdk_available:
            try:
                from google.antigravity import Agent, LocalAgentConfig  # type: ignore
                config = LocalAgentConfig(
                    system_instructions=(
                        "Bạn là RigMate, trợ lý hỗ trợ kiểm tra và tinh chỉnh rig 3D nhân vật "
                        "cho người dùng ít kiến thức 3D trong Blender hướng tới xuất Godot Engine."
                    )
                )
                async with Agent(config) as agent:
                    agent_resp = await asyncio.wait_for(
                        agent.chat(last_prompt),
                        timeout=timeout_seconds,
                    )
                    tokens = []
                    async for token in agent_resp:
                        tokens.append(token)
                    full_text = "".join(tokens)
                    return ProviderResponse(
                        text=full_text,
                        token_usage=TokenUsage.create(len(last_prompt) // 3, len(full_text) // 3),
                        suggested_actions=[],
                        raw_metadata={"backend": "sdk", "session_id": session_id},
                    )
            except Exception as e:
                return ProviderResponse(
                    text=f"[Lỗi kết nối Antigravity SDK]: {e}",
                    suggested_actions=["Chuyển sang Mock Provider"],
                    raw_metadata={"error": str(e)},
                )

        # Nếu có CLI `agy`
        if self.cli_path:
            try:
                # Gọi subprocess agy ở chế độ headless prompt
                process = await asyncio.create_subprocess_exec(
                    self.cli_path,
                    "--prompt",
                    last_prompt,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
                if process.returncode == 0:
                    out_text = stdout.decode("utf-8", errors="replace")
                    return ProviderResponse(
                        text=out_text,
                        token_usage=TokenUsage.create(len(last_prompt) // 3, len(out_text) // 3),
                        raw_metadata={"backend": "cli", "session_id": session_id},
                    )
                else:
                    err_text = stderr.decode("utf-8", errors="replace")
                    return ProviderResponse(
                        text=f"[Lỗi gọi CLI agy (exit code {process.returncode})]: {err_text}",
                        suggested_actions=["Xem log CLI"],
                    )
            except asyncio.TimeoutError:
                return ProviderResponse(
                    text=f"[Quá thời gian chờ]: Yêu cầu tới Antigravity CLI vượt quá {timeout_seconds}s.",
                    suggested_actions=["Thử lại", "Hủy"],
                )
            except Exception as e:
                return ProviderResponse(
                    text=f"[Lỗi thực thi agy CLI]: {e}",
                    suggested_actions=["Kiểm tra CLI"],
                )

        return ProviderResponse(text="Không thể khởi tạo provider.")

    async def stream_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        resp = await self.generate_response(messages, session_id)
        for chunk in resp.text.splitlines(keepends=True):
            yield chunk

    async def fetch_quota_snapshot(self, account_profile: str = "default") -> QuotaSnapshot:
        """
        Đọc hạn mức từ Antigravity:
        Hiện tại CLI/SDK chưa có API máy đọc công khai cho quota (/usage chỉ có TUI tương tác).
        Do đó hiển thị 'UNKNOWN' kèm nhãn rõ ràng: 'Chưa đọc được hạn mức tự động'.
        Tuyệt đối không đoán mò số liệu quota.
        """
        return QuotaSnapshot(
            provider_name="Antigravity",
            model_name=self._model,
            account_profile=account_profile,
            source="UNKNOWN",
            quota_remaining=None,
            quota_total=None,
            quota_unit="requests",
        )
