"""Localization and internationalization (i18n) layer for RigMate.

Canonical implementation lives in `rigmate.localization.engine` (pure standard library).
Re-exported here for backwards compatibility with core and external Python callers.
"""

from rigmate.localization.engine import (
    DEFAULT_LOCALE,
    TRANSLATIONS,
    set_locale,
    get_locale,
    get_available_locales,
    register_locale,
    t,
)

__all__ = [
    "DEFAULT_LOCALE",
    "TRANSLATIONS",
    "set_locale",
    "get_locale",
    "get_available_locales",
    "register_locale",
    "t",
]
