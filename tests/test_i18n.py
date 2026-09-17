"""Tests for the RigMate i18n / localization layer."""

import pytest
from rigmate.core.i18n import (
    t,
    set_locale,
    get_locale,
    register_locale,
    get_available_locales,
    DEFAULT_LOCALE,
)


def test_i18n_default_locale_is_english():
    set_locale("en")
    assert get_locale() == "en"
    assert DEFAULT_LOCALE == "en"


def test_i18n_translation_english_and_vietnamese():
    # English
    set_locale("en")
    assert t("status.disconnected") == "Disconnected from Bridge"
    assert t("quota.auto_unavailable") == "Automatic quota data is unavailable"
    assert t("status.connected", provider="MockAI") == "Connected (MockAI)"

    # Vietnamese
    set_locale("vi")
    assert t("status.disconnected") == "Chưa kết nối Bridge"
    assert t("quota.auto_unavailable") == "Chưa đọc được hạn mức tự động"
    assert t("status.connected", provider="MockAI") == "Đã kết nối (MockAI)"

    # Restore default
    set_locale("en")


def test_i18n_fallback_to_english():
    # Add a key only in English
    register_locale("en", {"test.english_only": "English only string: {value}"})
    
    set_locale("vi")
    # Missing in Vietnamese, falls back to English
    assert t("test.english_only", value="abc") == "English only string: abc"
    set_locale("en")


def test_i18n_fallback_to_key():
    set_locale("en")
    # Missing everywhere returns the key itself
    assert t("non_existent.dummy_key") == "non_existent.dummy_key"


def test_i18n_register_new_locale():
    # Register Spanish 'es'
    register_locale("es", {
        "status.disconnected": "Desconectado de Bridge",
        "btn.send": "Enviar",
    })
    assert "es" in get_available_locales()

    set_locale("es")
    assert t("status.disconnected") == "Desconectado de Bridge"
    assert t("btn.send") == "Enviar"
    # Fallback to English for unprovided keys in Spanish
    set_locale("en")


def test_i18n_unknown_locale_safely_falls_back():
    set_locale("unsupported_locale_xyz")
    assert get_locale() == "en"
    assert t("status.disconnected") == "Disconnected from Bridge"


def test_i18n_error_codes_separate_from_ui():
    """Verify that error identifiers/exceptions are stable and UI can translate them."""
    from rigmate.blender_addon.client import (
        BridgeClientError,
        BridgeConnectionError,
        BridgeAuthError,
        BridgeTimeoutError,
    )

    err = BridgeConnectionError("Cannot connect to 127.0.0.1:8765")
    # Internal error message remains English
    assert "Cannot connect" in str(err)
    assert err.error_code == "bridge.connection_failed"

    # UI can translate error_code
    set_locale("en")
    assert "Unable to connect" in t(f"error.{err.error_code}")

    set_locale("vi")
    assert "Không thể kết nối Bridge" in t(f"error.{err.error_code}")

    set_locale("en")

