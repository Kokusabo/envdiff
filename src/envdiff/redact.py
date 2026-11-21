"""Hide secret values in CLI output."""

from __future__ import annotations

import re

SECRET_MARKERS = (
    "KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE", "CREDENTIAL", "DSN", "AUTH",
)
MASK = "********"

# The userinfo part of a URL: scheme://USERINFO@host
_URL_USERINFO = re.compile(r"://([^/@\s]+)@")


def is_secret_key(key: str) -> bool:
    """Return True if the key name looks like it holds a secret."""
    upper = key.upper()
    return any(marker in upper for marker in SECRET_MARKERS)


def _mask_userinfo(match: re.Match[str]) -> str:
    user, sep, _password = match.group(1).partition(":")
    if sep:
        # user:password@ -> keep the user name, hide the password
        return f"://{user}:{MASK}@"
    # token@ (Sentry DSN, https://TOKEN@github.com, ...) -> hide it all
    return f"://{MASK}@"


def mask_url_password(value: str) -> str:
    """Hide credentials inside URLs: passwords, and tokens used as the user name."""
    return _URL_USERINFO.sub(_mask_userinfo, value)


def display_value(key: str, value: str) -> str:
    """Value as it should appear in output: masked for secrets, shown otherwise."""
    if value == "":
        return "(empty)"
    if is_secret_key(key):
        return MASK
    return mask_url_password(value)
