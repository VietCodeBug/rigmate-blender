"""Tests for provider responses, unverified environment handling, timeout, and cancellation."""

import asyncio
import pytest
from rigmate.providers.base import ChatMessage
from rigmate.providers.mock_provider import MockAIProvider
from rigmate.providers.antigravity_provider import AntigravityProvider
from rigmate.bridge.session import SessionManager
from rigmate.storage.manager import StorageManager


def test_mock_provider_responses():
    provider = MockAIProvider()
    assert provider.provider_id == "mock"

    msgs = [ChatMessage(role="user", content="I want to inspect character model")]
    resp = asyncio.run(provider.generate_response(msgs, session_id="s1"))

    assert resp.text is not None
    assert "Hunyuan 3D" in resp.text
    assert resp.token_usage is not None
    assert resp.token_usage.total_tokens > 0

    # Quota demo
    quota = asyncio.run(provider.fetch_quota_snapshot())
    assert quota.source == "DEMO"
    assert quota.percentage == 75.0


def test_antigravity_provider_unverified_fallback():
    # Without agy CLI or SDK installed, provider returns UNVERIFIED_ENV gracefully without crashing
    provider = AntigravityProvider()

    # Simulate environment without CLI
    provider.cli_path = None
    provider.sdk_available = False

    msgs = [ChatMessage(role="user", content="Hello")]
    resp = asyncio.run(provider.generate_response(msgs, session_id="s_anti"))

    assert "UNVERIFIED_ENV" in resp.text
    assert resp.raw_metadata.get("status") == "UNVERIFIED_ENV"

    # Quota reported as UNKNOWN
    quota = asyncio.run(provider.fetch_quota_snapshot())
    assert quota.source == "UNKNOWN"
    assert quota.quota_remaining is None


def test_session_manager_and_cancellation(temp_storage_dir):
    async def _async_flow():
        storage = StorageManager(base_dir=temp_storage_dir)
        session_mgr = SessionManager(storage)
        provider = MockAIProvider()

        session = session_mgr.create_session(provider)
        assert session.session_id is not None

        # Send message
        resp = await session_mgr.send_message(
            session_id=session.session_id,
            user_message="Hello RigMate",
            provider=provider,
        )
        assert resp.text is not None
        assert len(session.messages) == 2  # user + assistant

        # Check storage persistence
        saved_history = storage.load_chat_history(session.session_id)
        assert len(saved_history) == 2

        # Task cancellation test
        task = asyncio.create_task(
            session_mgr.send_message(
                session_id=session.session_id,
                user_message="A long-running request...",
                provider=provider,
                timeout_seconds=10.0,
            )
        )
        # Cancel immediately
        await asyncio.sleep(0.01)
        cancelled = session_mgr.cancel_active_request(session.session_id)
        assert cancelled is True

        result_resp = await task
        assert "[Cancelled]" in result_resp.text

    asyncio.run(_async_flow())

