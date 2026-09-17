"""Session management, timeout handling and request cancellation."""

import asyncio
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from rigmate.providers.base import ChatMessage, ProviderResponse, BaseAIProvider
from rigmate.storage.manager import StorageManager


class SessionState(BaseModel):
    """Conversation session state."""
    session_id: str
    provider_id: str
    model_name: str
    messages: List[ChatMessage] = Field(default_factory=list)
    total_tokens_used: int = 0
    is_active: bool = True


class SessionManager:
    """Manage lifecycle of chat sessions and active async tasks."""

    def __init__(self, storage: Optional[StorageManager] = None):
        self.storage = storage or StorageManager()
        self.sessions: Dict[str, SessionState] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    def create_session(self, provider: BaseAIProvider) -> SessionState:
        """Create a new unique conversation session."""
        s_id = str(uuid.uuid4())
        state = SessionState(
            session_id=s_id,
            provider_id=provider.provider_id,
            model_name=provider.model_name,
        )
        self.sessions[s_id] = state
        self.storage.save_chat_history(s_id, [])
        return state

    def get_or_create_session(self, session_id: Optional[str], provider: BaseAIProvider) -> SessionState:
        """Retrieve active session or create a new one."""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        if session_id:
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
        """Send message, append history and allow cancellation via session_id."""
        session = self.get_or_create_session(session_id, provider)

        user_msg = ChatMessage(role="user", content=user_message, context_data=context_data)
        session.messages.append(user_msg)

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
            asst_msg = ChatMessage(role="assistant", content=response.text)
            session.messages.append(asst_msg)

            if response.token_usage:
                session.total_tokens_used += response.token_usage.total_tokens

            self.storage.save_chat_history(
                session.session_id,
                [m.model_dump() for m in session.messages],
            )

            return response
        except asyncio.CancelledError:
            return ProviderResponse(
                text="[Cancelled]: Request processing was cancelled by user.",
                suggested_actions=["Retry"],
            )
        except asyncio.TimeoutError:
            return ProviderResponse(
                text=f"[Timeout]: No response received within {timeout_seconds} seconds.",
                suggested_actions=["Retry", "Check Connection"],
            )
        finally:
            self.running_tasks.pop(session_id, None)

    def cancel_active_request(self, session_id: str) -> bool:
        """Cancel active async request task if running."""
        task = self.running_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
