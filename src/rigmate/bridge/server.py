"""Server Bridge giao tiếp cục bộ (Localhost only) giữa Blender Add-on và AI Engine."""

import secrets
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from rigmate.core.quota import QuotaSnapshot
from rigmate.providers.base import BaseAIProvider
from rigmate.providers.mock_provider import MockAIProvider
from rigmate.providers.antigravity_provider import AntigravityProvider
from rigmate.bridge.session import SessionManager
from rigmate.storage.manager import StorageManager
from rigmate.storage.runtime_state import RuntimeStateManager, BridgeRuntimeState


class ChatRequestPayload(BaseModel):
    session_id: Optional[str] = None
    message: str
    context_data: Optional[Dict[str, Any]] = None


class CancelRequestPayload(BaseModel):
    session_id: str


class ManualQuotaPayload(BaseModel):
    provider_name: str
    model_name: str
    account_profile: str = "default"
    quota_remaining: float
    quota_total: Optional[float] = None
    quota_unit: str = "requests"
    plan_expiration: Optional[str] = None


class BridgeServer:
    """
    HTTP/REST Bridge server chỉ lắng nghe localhost (127.0.0.1)
    Bảo vệ bằng token xác thực ngẫu nhiên sinh khi khởi động.
    Ghi runtime state vào AppData để Blender Add-on phát hiện tự động an toàn.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, save_state: bool = True):
        self.host = host
        self.port = port
        self.auth_token = secrets.token_hex(16)
        self.storage = StorageManager()
        self.session_manager = SessionManager(self.storage)
        self.state_manager = RuntimeStateManager(self.storage.base_dir)

        # Mặc định khởi động với MockProvider an toàn
        self.current_provider: BaseAIProvider = MockAIProvider()

        if save_state:
            self._publish_runtime_state()

        self.app = self._create_app()

    def _publish_runtime_state(self):
        """Xuất thông tin runtime state cho các process cục bộ khác (Blender)."""
        state = BridgeRuntimeState(
            host=self.host,
            port=self.port,
            auth_token=self.auth_token,
        )
        self.state_manager.save_state(state)

    def cleanup_state(self):
        """Dọn dẹp state khi tắt server."""
        self.state_manager.clear_state()

    def set_provider(self, provider: BaseAIProvider):
        self.current_provider = provider

    def _verify_token(self, x_rigmate_token: Optional[str] = Header(None)):
        if not x_rigmate_token or x_rigmate_token != self.auth_token:
            raise HTTPException(status_code=401, detail="Xác thực cục bộ thất bại (Invalid Auth Token).")

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="RigMate Local Bridge", version="0.1.0")

        @app.get("/health")
        async def health():
            return {
                "status": "online",
                "provider": self.current_provider.provider_id,
                "model": self.current_provider.model_name,
            }

        @app.post("/chat", dependencies=[Depends(self._verify_token)])
        async def chat(payload: ChatRequestPayload):
            session = self.session_manager.get_or_create_session(
                payload.session_id,
                self.current_provider,
            )
            response = await self.session_manager.send_message(
                session_id=session.session_id,
                user_message=payload.message,
                provider=self.current_provider,
                context_data=payload.context_data,
            )
            return {
                "session_id": session.session_id,
                "response": response.model_dump(),
            }

        @app.post("/cancel", dependencies=[Depends(self._verify_token)])
        async def cancel(payload: CancelRequestPayload):
            cancelled = self.session_manager.cancel_active_request(payload.session_id)
            return {"cancelled": cancelled}

        @app.get("/quota", dependencies=[Depends(self._verify_token)])
        async def get_quota(profile: str = "default"):
            # Thử đọc từ provider nếu là quota provider
            if hasattr(self.current_provider, "fetch_quota_snapshot"):
                snapshot = await self.current_provider.fetch_quota_snapshot(profile)  # type: ignore
                # Nếu không đọc tự động được, tìm snapshot nhập thủ công đã lưu trong storage
                if snapshot.source == "UNKNOWN":
                    saved = self.storage.load_quota_snapshot(
                        profile,
                        self.current_provider.provider_id,
                        self.current_provider.model_name,
                    )
                    if saved:
                        return saved.model_dump()
                return snapshot.model_dump()

            return {"source": "UNKNOWN", "quota_remaining": None}

        @app.post("/quota/manual", dependencies=[Depends(self._verify_token)])
        async def update_manual_quota(payload: ManualQuotaPayload):
            snapshot = QuotaSnapshot(
                provider_name=payload.provider_name,
                model_name=payload.model_name,
                account_profile=payload.account_profile,
                source="MANUAL",
                quota_remaining=payload.quota_remaining,
                quota_total=payload.quota_total,
                quota_unit=payload.quota_unit,
                plan_expiration=payload.plan_expiration,
            )
            self.storage.save_quota_snapshot(snapshot)
            return {"status": "saved", "snapshot": snapshot.model_dump()}

        @app.get("/history/{session_id}", dependencies=[Depends(self._verify_token)])
        async def get_history(session_id: str):
            messages = self.storage.load_chat_history(session_id)
            return {"session_id": session_id, "messages": messages}

        @app.delete("/history", dependencies=[Depends(self._verify_token)])
        async def clear_history():
            self.storage.clear_all_history()
            return {"status": "cleared"}

        return app
