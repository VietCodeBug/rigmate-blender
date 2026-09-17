"""Tests for Session Continuity across messages and cancellation endpoint."""

import asyncio
import pytest
from fastapi.testclient import TestClient
from rigmate.bridge.server import BridgeServer
from rigmate.storage.manager import StorageManager
from rigmate.bridge.session import SessionManager
from rigmate.providers.mock_provider import MockAIProvider


def test_session_continuity_across_messages():
    server = BridgeServer(save_state=False)
    client = TestClient(server.app)
    headers = {"x-rigmate-token": server.auth_token}

    # Message 1: No session_id sent -> Server creates fresh session_id
    r1 = client.post("/chat", json={"message": "I am a 3D Artist"}, headers=headers)
    assert r1.status_code == 200
    s_id = r1.json()["session_id"]
    assert s_id is not None

    # Message 2: Sending same session_id -> Server continues session
    r2 = client.post("/chat", json={"session_id": s_id, "message": "Inspect my model"}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["session_id"] == s_id

    # Verify history in session_manager has 4 messages (2 user + 2 assistant)
    session_state = server.session_manager.sessions.get(s_id)
    assert session_state is not None
    assert len(session_state.messages) == 4


def test_new_session_isolation():
    server = BridgeServer(save_state=False)
    client = TestClient(server.app)
    headers = {"x-rigmate-token": server.auth_token}

    # Session 1
    r1 = client.post("/chat", json={"message": "First inquiry"}, headers=headers)
    s1 = r1.json()["session_id"]

    # New session clicked (UI clears active_session_id and sends None)
    r2 = client.post("/chat", json={"message": "Second inquiry in isolated session"}, headers=headers)
    s2 = r2.json()["session_id"]

    assert s1 != s2
    assert s1 in server.session_manager.sessions
    assert s2 in server.session_manager.sessions


def test_cancellation_endpoint():
    server = BridgeServer(save_state=False)
    client = TestClient(server.app)
    headers = {"x-rigmate-token": server.auth_token}

    # Call cancel on a session with no active running task
    r_cancel = client.post("/cancel", json={"session_id": "non_running_session"}, headers=headers)
    assert r_cancel.status_code == 200
    assert r_cancel.json()["cancelled"] is False
