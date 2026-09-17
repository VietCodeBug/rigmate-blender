"""Localization and internationalization (i18n) layer for RigMate.

Canonical implementation lives in `rigmate.blender_addon.i18n` (Blender-safe, stdlib only).
Re-exported here for backwards compatibility with core and external Python callers.
"""

from rigmate.blender_addon.i18n import (
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
