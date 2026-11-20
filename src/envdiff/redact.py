"""Hide secret values in CLI output."""

from __future__ import annotations

import re

SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE", "CREDENTIAL")
MASK = "********"

# Matches the userinfo of a URL: everything between "://" and the last "@" before
# the host, so passwords that themselves contain "@" are covered too.
_URL_USERINFO = re.compile(r"(://)([^/?#\s]*)(@)")


def is_secret_key(key: str) -> bool:
    """Return True if the key name looks like it holds a secret."""
    upper = key.upper()
    return any(marker in upper for marker in SECRET_MARKERS)


def _mask_userinfo(match: re.Match[str]) -> str:
    userinfo = match.group(2)
    user, sep, _password = userinfo.partition(":")
    # user:password keeps the user name; a bare token (https://TOKEN@host) is hidden.
    masked = f"{user}:{MASK}" if sep else MASK
    return f"{match.group(1)}{masked}{match.group(3)}"


def mask_url_password(value: str) -> str:
    """Hide credentials inside URLs: the password, or a token used as the user name."""
    return _URL_USERINFO.sub(_mask_userinfo, value)


def display_value(key: str, value: str) -> str:
    """Value as it should appear in output: masked for secrets, shown otherwise."""
    if value == "":
        return "(empty)"
    if is_secret_key(key):
        return MASK
    return mask_url_password(value)
