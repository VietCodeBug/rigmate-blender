"""Mock Provider mô phỏng chính xác ngữ cảnh quy trình Hunyuan 3D + Meshy + Godot."""

import asyncio
from typing import AsyncGenerator, List
from rigmate.core.quota import QuotaSnapshot, TokenUsage
from rigmate.providers.base import BaseAIProvider, BaseQuotaProvider, ChatMessage, ProviderResponse


class MockAIProvider(BaseAIProvider, BaseQuotaProvider):
    """
    Provider mô phỏng phục vụ phát triển khi chưa có CLI Antigravity hoặc môi trường Blender.
    Hỗ trợ kịch bản thông minh dựa trên nội dung câu hỏi của người dùng.
    """

    def __init__(self, model: str = "mock-hunyuan-assistant-v1"):
        self._model = model

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
        timeout_seconds: float = 30.0,
    ) -> ProviderResponse:
        await asyncio.sleep(0.3)  # Giả lập độ trễ mạng thực tế

        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content.lower()
                break

        # Kịch bản phản hồi theo từ khóa
        if "kiểm tra" in last_user_msg or "diagnose" in last_user_msg or "chẩn đoán" in last_user_msg:
            resp_text = (
                "[Mô phỏng] Đã kiểm tra mô hình trong Scene:\n"
                "- Nhận diện Mesh Hunyuan 3D (~52,400 đỉnh): Số lượng đỉnh tương đối cao, "
                "khuyến nghị Decimate khoảng 40-50% nếu chuẩn bị xuất sang Godot Engine.\n"
                "- Armature Meshy: Phát hiện 52 xương. Chưa nhận diện được đầy đủ 5 ngón tay tách rời "
                "(thường do model dạng bàn tay nắm).\n"
                "- Cần Apply Transforms (Ctrl+A) trước khi điều chỉnh trọng số."
            )
            actions = ["Apply Transforms", "Kiểm tra Weights", "Thêm ngón tay"]
        elif "ngón" in last_user_msg or "finger" in last_user_msg:
            resp_text = (
                "[Mô phỏng] Về xương ngón tay:\n"
                "Mô hình tạo từ Hunyuan 3D thường có các ngón dính liền hoặc topology không chia 5 ngón rõ rệt. "
                "Meshy khi tạo auto-rig có thể chỉ gắn xương cổ tay. "
                "Trong bản RigMate v0.2, công cụ sẽ hỗ trợ sinh 5 chuỗi xương ngón tự động theo tỷ lệ bàn tay."
            )
            actions = ["Tạo chuỗi xương ngón", "Xem tài liệu topology"]
        elif "godot" in last_user_msg:
            resp_text = (
                "[Mô phỏng] Khuyến nghị xuất sang Godot Engine:\n"
                "1. Định dạng ưu tiên: glTF 2.0 (.glb) hoặc .tscn.\n"
                "2. Giới hạn trọng số vertex: Godot mặc định hỗ trợ 4 weights/vertex (có thể bật 8-weights trong Project Settings).\n"
                "3. Kiểm tra tên root bone (thường là Hips hoặc Root) để tương thích animation tree."
            )
            actions = ["Kiểm tra tương thích glTF", "Giảm số đỉnh cho Godot"]
        else:
            resp_text = (
                f"[Mô phỏng] RigMate đã nhận câu hỏi: '{last_user_msg}'. "
                "Hệ thống đang hoạt động ở chế độ Mock Provider (phù hợp phát triển khi chưa kết nối CLI Antigravity)."
            )
            actions = ["Chẩn đoán Rig", "Hỏi về xuất Godot"]

        # Giả lập số token tiêu thụ cho lượt này
        token_usage = TokenUsage.create(
            prompt=len(last_user_msg) // 3 + 20,
            completion=len(resp_text) // 3,
        )

        return ProviderResponse(
            text=resp_text,
            token_usage=token_usage,
            suggested_actions=actions,
            raw_metadata={"mode": "mock", "session_id": session_id},
        )

    async def stream_response(
        self,
        messages: List[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        full_resp = await self.generate_response(messages, session_id)
        words = full_resp.text.split(" ")
        for w in words:
            yield w + " "
            await asyncio.sleep(0.04)

    async def fetch_quota_snapshot(self, account_profile: str = "default") -> QuotaSnapshot:
        """
        Trả về snapshot mô phỏng: Đánh dấu rõ ràng 'DEMO'.
        Không giả lập 100% như dữ liệu thật.
        """
        return QuotaSnapshot(
            provider_name="MockProvider",
            model_name=self._model,
            account_profile=account_profile,
            source="DEMO",
            quota_remaining=75.0,
            quota_total=100.0,
            quota_unit="requests",
            reset_at="2026-09-18T00:00:00Z",
            plan_expiration="2026-10-01T00:00:00Z",
        )
