"""Unit tests for recursive data redaction."""

from rigmate.core.redaction import redact_sensitive_data


def test_redact_nested_dictionary():
    raw = {
        "user_id": "artist_42",
        "auth_token": "secret_hex_1234567890abcdef",
        "api_key": "sk-live-xyz987",
        "config": {
            "endpoint": "http://127.0.0.1:8765",
            "x-rigmate-token": "runtime_tok_abc",
            "preferences": {"theme": "dark", "locale": "en"},
        },
    }

    cleaned = redact_sensitive_data(raw)

    # Verify redaction
    assert cleaned["auth_token"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["config"]["x-rigmate-token"] == "[REDACTED]"

    # Safe values unchanged
    assert cleaned["user_id"] == "artist_42"
    assert cleaned["config"]["endpoint"] == "http://127.0.0.1:8765"
    assert cleaned["config"]["preferences"]["locale"] == "en"

    # Verify input object is not mutated
    assert raw["auth_token"] == "secret_hex_1234567890abcdef"


def test_redact_lists_and_mixed_case():
    raw = [
        {"Name": "Item 1", "PASSWORD": "my_password_123"},
        {"API_KEY": "key456", "data": [1, 2, {"token": "sub_tok"}]},
    ]

    cleaned = redact_sensitive_data(raw, replacement="<MASKED>")
    assert cleaned[0]["PASSWORD"] == "<MASKED>"
    assert cleaned[0]["Name"] == "Item 1"
    assert cleaned[1]["API_KEY"] == "<MASKED>"
    assert cleaned[1]["data"][2]["token"] == "<MASKED>"
