"""Parse .env files into an ordered mapping of key -> value."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

BOM = "﻿"


@dataclass
class ParseResult:
    """Parsed variables plus human-readable warnings about the source text."""

    values: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _unquote(value: str) -> str | None:
    """Return the value inside matching quotes, or None if it is not quoted.

    Anything after the closing quote (such as ` # comment`) is ignored.
    """
    if not value or value[0] not in ("'", '"'):
        return None
    quote = value[0]
    end = value.find(quote, 1)
    if end == -1:
        return None
    inner = value[1:end]
    if quote == '"':
        inner = inner.replace('\\"', '"').replace("\\n", "\n")
    return inner


def _strip_inline_comment(value: str) -> str:
    """Remove a trailing ` # comment` from an unquoted value."""
    for marker in (" #", "\t#"):
        idx = value.find(marker)
        if idx != -1:
            value = value[:idx]
    return value.rstrip()


def parse_env_detailed(text: str) -> ParseResult:
    """Parse the text of a .env file and collect warnings.

    Supports comments (`#`), blank lines, an optional `export ` prefix,
    a UTF-8 byte order mark, CRLF line endings, single- and double-quoted
    values (with a trailing comment allowed), and inline comments on unquoted
    values. Keys with empty values are kept with an empty string.

    Warnings report lines that could not be parsed and keys defined more than
    once (the last definition wins, as most loaders do).
    """
    result = ParseResult()
    text = text.lstrip(BOM)
    seen_lines: dict[str, int] = {}

    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            result.warnings.append(f"line {number}: no '=' found, line ignored")
            continue
        key, _, raw_value = line.partition("=")
        key = key.strip()
        if not key or " " in key:
            result.warnings.append(f"line {number}: invalid key {key!r}, line ignored")
            continue

        raw_value = raw_value.strip()
        quoted = _unquote(raw_value)
        value = quoted if quoted is not None else _strip_inline_comment(raw_value)

        if key in seen_lines:
            result.warnings.append(
                f"line {number}: {key} already defined on line {seen_lines[key]}, "
                "using this value"
            )
        seen_lines[key] = number
        result.values[key] = value
    return result


def parse_env(text: str) -> dict[str, str]:
    """Parse the text of a .env file and return only the variables."""
    return parse_env_detailed(text).values


def load_env_detailed(path: str | Path) -> ParseResult:
    """Read a .env file from disk and return values plus warnings."""
    return parse_env_detailed(Path(path).read_text(encoding="utf-8"))


def load_env(path: str | Path) -> dict[str, str]:
    """Read and parse a .env file from disk."""
    return load_env_detailed(path).values
