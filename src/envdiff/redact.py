"""Hide secret values in CLI output."""

from __future__ import annotations

import re

SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE", "CREDENTIAL")
MASK = "********"

# Matches the password part of URLs such as postgres://user:PASS@host/db.
_URL_PASSWORD = re.compile(r"(://[^:/@\s]+:)([^@\s]+)(@)")


def is_secret_key(key: str) -> bool:
    """Return True if the key name looks like it holds a secret."""
    upper = key.upper()
    return any(marker in upper for marker in SECRET_MARKERS)


def mask_url_password(value: str) -> str:
    """Replace the password inside a URL's userinfo with the mask."""
    return _URL_PASSWORD.sub(lambda m: f"{m.group(1)}{MASK}{m.group(3)}", value)


def display_value(key: str, value: str) -> str:
    """Value as it should appear in output: masked for secrets, shown otherwise."""
    if value == "":
        return "(empty)"
    if is_secret_key(key):
        return MASK
    return mask_url_password(value)
