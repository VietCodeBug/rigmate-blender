"""RigMate neutral localization package.

Pure Python standard library i18n and translation engine.
Zero external dependencies.
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
