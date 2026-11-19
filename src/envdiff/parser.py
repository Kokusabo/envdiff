"""Parse .env files into an ordered mapping of key -> value."""

from __future__ import annotations

from pathlib import Path


def _strip_inline_comment(value: str) -> str:
    """Remove a trailing ` # comment` from an unquoted value."""
    for marker in (" #", "\t#"):
        idx = value.find(marker)
        if idx != -1:
            value = value[:idx]
    return value.rstrip()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\n", "\n")
        return inner
    return _strip_inline_comment(value)


def parse_env(text: str) -> dict[str, str]:
    """Parse the text of a .env file.

    Supports comments (`#`), blank lines, an optional `export ` prefix,
    single- and double-quoted values, and inline comments on unquoted values.
    Keys with empty values are kept with an empty string.
    Later duplicates override earlier ones, as most loaders do.
    """
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        result[key] = _unquote(value.strip())
    return result


def load_env(path: str | Path) -> dict[str, str]:
    """Read and parse a .env file from disk."""
    return parse_env(Path(path).read_text(encoding="utf-8"))
