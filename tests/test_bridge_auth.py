"""Integration tests for Bridge Server: Authentication handshake, health, and unauthorized rejection."""

import pytest
from fastapi.testclient import TestClient
from rigmate.bridge.server import BridgeServer


def test_bridge_health_endpoint():
    server = BridgeServer(save_state=False)
    client = TestClient(server.app)

    # Health endpoint does not require auth
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert data["provider"] == "mock"


def test_bridge_authentication_enforcement():
    server = BridgeServer(save_state=False)
    client = TestClient(server.app)

    # 1. Post to /chat without token -> 401 Unauthorized
    resp_no_token = client.post("/chat", json={"message": "hello"})
    assert resp_no_token.status_code == 401
    assert "Invalid Auth Token" in resp_no_token.json()["detail"]

    # 2. Post to /chat with invalid token -> 401 Unauthorized
    resp_bad_token = client.post(
        "/chat",
        json={"message": "hello"},
        headers={"x-rigmate-token": "wrong_token_123"},
    )
    assert resp_bad_token.status_code == 401

    # 3. Post to /chat with valid server runtime token -> 200 OK
    valid_token = server.auth_token
    resp_valid = client.post(
        "/chat",
        json={"message": "hello RigMate"},
        headers={"x-rigmate-token": valid_token},
    )
    assert resp_valid.status_code == 200
    assert "session_id" in resp_valid.json()
    assert "response" in resp_valid.json()


def test_bridge_quota_manual_and_read_roundtrip():
    server = BridgeServer(save_state=False)
    client = TestClient(server.app)
    headers = {"x-rigmate-token": server.auth_token}

    # 1. Call POST /quota/manual to save snapshot
    payload = {
        "provider_name": "Antigravity",
        "model_name": "gemini-3.8-flash",
        "account_profile": "artist_a",
        "quota_remaining": 88.0,
        "quota_total": 100.0,
        "quota_unit": "requests",
    }
    res_post = client.post("/quota/manual", json=payload, headers=headers)
    assert res_post.status_code == 200
    assert res_post.json()["status"] == "saved"

    # 2. Read back snapshot via StorageManager
    saved = server.storage.load_quota_snapshot("artist_a", "Antigravity", "gemini-3.8-flash")
    assert saved is not None
    assert saved.source == "MANUAL"
    assert saved.quota_remaining == 88.0
    assert saved.percentage == 88.0
