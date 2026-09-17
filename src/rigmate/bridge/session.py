"""Quản lý các phiên hội thoại (Session), timeout và hủy tác vụ (cancellation)."""

import asyncio
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from rigmate.providers.base import ChatMessage, ProviderResponse, BaseAIProvider
from rigmate.storage.manager import StorageManager


class SessionState(BaseModel):
    """Trạng thái một phiên hội thoại."""
    session_id: str
    provider_id: str
    model_name: str
    messages: List[ChatMessage] = Field(default_factory=list)
    total_tokens_used: int = 0
    is_active: bool = True


class SessionManager:
    """Quản lý vòng đời phiên chat và các tác vụ đang chạy."""

    def __init__(self, storage: Optional[StorageManager] = None):
        self.storage = storage or StorageManager()
        self.sessions: Dict[str, SessionState] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    def create_session(self, provider: BaseAIProvider) -> SessionState:
        """Tạo một phiên hội thoại mới hoàn toàn."""
        s_id = str(uuid.uuid4())
        state = SessionState(
            session_id=s_id,
            provider_id=provider.provider_id,
            model_name=provider.model_name,
        )
        self.sessions[s_id] = state
        # Lưu vào storage local
        self.storage.save_chat_history(s_id, [])
        return state

    def get_or_create_session(self, session_id: Optional[str], provider: BaseAIProvider) -> SessionState:
        """Lấy phiên hiện tại hoặc tạo mới nếu chưa tồn tại."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        if session_id:
            # Thử tải từ storage
            saved_msgs = self.storage.load_chat_history(session_id)
            if saved_msgs:
                state = SessionState(
                    session_id=session_id,
                    provider_id=provider.provider_id,
                    model_name=provider.model_name,
                    messages=[ChatMessage(**m) for m in saved_msgs],
                )
                self.sessions[session_id] = state
                return state

        return self.create_session(provider)

    async def send_message(
        self,
        session_id: str,
        user_message: str,
        provider: BaseAIProvider,
        context_data: Optional[dict] = None,
        timeout_seconds: float = 45.0,
    ) -> ProviderResponse:
        """Gửi tin nhắn, lưu lịch sử và hỗ trợ hủy tác vụ qua session_id."""
        session = self.get_or_create_session(session_id, provider)

        # Thêm tin nhắn user vào lịch sử
        user_msg = ChatMessage(role="user", content=user_message, context_data=context_data)
        session.messages.append(user_msg)

        # Tạo task có thể hủy được
        task = asyncio.create_task(
            provider.generate_response(
                session.messages,
                session_id=session.session_id,
                timeout_seconds=timeout_seconds,
            )
        )
        self.running_tasks[session_id] = task

        try:
            response = await asyncio.wait_for(task, timeout=timeout_seconds)
            # Thêm phản hồi assistant vào lịch sử
            asst_msg = ChatMessage(role="assistant", content=response.text)
            session.messages.append(asst_msg)

            if response.token_usage:
                session.total_tokens_used += response.token_usage.total_tokens

            # Lưu vào local storage
            self.storage.save_chat_history(
                session.session_id,
                [m.model_dump() for m in session.messages],
            )

            return response
        except asyncio.CancelledError:
            return ProviderResponse(
                text="[Đã hủy]: Yêu cầu xử lý đã được dừng bởi người dùng.",
                suggested_actions=["Gửi lại"],
            )
        except asyncio.TimeoutError:
            return ProviderResponse(
                text=f"[Quá thời gian chờ]: Không nhận được phản hồi sau {timeout_seconds} giây.",
                suggested_actions=["Thử lại", "Kiểm tra kết nối"],
            )
        finally:
            self.running_tasks.pop(session_id, None)

    def cancel_active_request(self, session_id: str) -> bool:
        """Hủy yêu cầu đang thực thi nếu có."""
        task = self.running_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
