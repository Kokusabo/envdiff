"""Hide secret values in CLI output."""

from __future__ import annotations

SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE", "CREDENTIAL")
MASK = "********"


def is_secret_key(key: str) -> bool:
    """Return True if the key name looks like it holds a secret."""
    upper = key.upper()
    return any(marker in upper for marker in SECRET_MARKERS)


def display_value(key: str, value: str) -> str:
    """Value as it should appear in output: masked for secrets, shown otherwise."""
    if value == "":
        return "(empty)"
    if is_secret_key(key):
        return MASK
    return value
