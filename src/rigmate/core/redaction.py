"""Recursive redaction utility for logs, diagnostics, and support bundles.

Safely scrubs sensitive tokens, passwords, and credentials while preserving data structure.
Does NOT mutate the original object.
"""

from typing import Any, Dict, List, Set, Union

DEFAULT_SENSITIVE_KEYS: Set[str] = {
    "token",
    "auth_token",
    "x-rigmate-token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "credential",
    "credentials",
    "private_key",
    "access_token",
    "refresh_token",
}


def redact_sensitive_data(
    data: Any,
    replacement: str = "[REDACTED]",
    sensitive_keys: Union[Set[str], List[str]] = DEFAULT_SENSITIVE_KEYS,
) -> Any:
    """
    Recursively redact sensitive keys in nested dicts and lists.
    Returns a new deeply cleaned copy without modifying the input object.
    """
    keys_set = {k.lower() for k in sensitive_keys}

    if isinstance(data, dict):
        cleaned_dict: Dict[str, Any] = {}
        for k, v in data.items():
            k_lower = str(k).lower().replace("-", "_")
            if k_lower in keys_set or any(sk in k_lower for sk in ["token", "secret", "password", "api_key"]):
                cleaned_dict[k] = replacement
            else:
                cleaned_dict[k] = redact_sensitive_data(v, replacement, keys_set)
        return cleaned_dict

    elif isinstance(data, list):
        return [redact_sensitive_data(item, replacement, keys_set) for item in data]

    elif isinstance(data, tuple):
        return tuple(redact_sensitive_data(item, replacement, keys_set) for item in data)

    return data
