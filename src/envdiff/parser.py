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


# Escape sequences understood inside double quotes. Anything else is kept as written.
_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}


def _find_closing_quote(value: str, quote: str) -> int:
    """Index of the quote that closes `value[0]`, or -1 if there is none.

    Inside double quotes a backslash escapes the next character.
    """
    i = 1
    while i < len(value):
        char = value[i]
        if quote == '"' and char == "\\":
            i += 2
            continue
        if char == quote:
            return i
        i += 1
    return -1


def _unescape(value: str) -> str:
    """Decode escapes in a double-quoted value in a single pass."""
    out: list[str] = []
    i = 0
    while i < len(value):
        char = value[i]
        if char == "\\" and i + 1 < len(value) and value[i + 1] in _ESCAPES:
            out.append(_ESCAPES[value[i + 1]])
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


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
    values (with a trailing comment allowed), quoted values that span several
    lines, and inline comments on unquoted values. Keys with empty values are
    kept with an empty string.

    Warnings report lines that could not be parsed, quotes that are never
    closed, and keys defined more than once (the last definition wins, as most
    loaders do).
    """
    result = ParseResult()
    lines = text.lstrip(BOM).splitlines()
    seen_lines: dict[str, int] = {}
    index = 0

    while index < len(lines):
        number = index + 1
        line = lines[index].strip()
        index += 1
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            result.warnings.append(f"line {number}: no '=' found, line ignored")
            continue
        key, _, raw_value = line.partition("=")
        key = key.strip()
        if not key or any(char.isspace() for char in key):
            result.warnings.append(f"line {number}: invalid key {key!r}, line ignored")
            continue

        raw_value = raw_value.strip()
        value: str | None = None
        if raw_value[:1] in ("'", '"'):
            quote = raw_value[0]
            joined = raw_value
            end = _find_closing_quote(joined, quote)
            next_index = index
            # A quoted value may continue on the following lines.
            while end == -1 and next_index < len(lines):
                joined += "\n" + lines[next_index]
                next_index += 1
                end = _find_closing_quote(joined, quote)
            if end == -1:
                result.warnings.append(
                    f"line {number}: {key} has an unclosed {quote} quote, value used as written"
                )
            else:
                index = next_index
                inner = joined[1:end]
                value = _unescape(inner) if quote == '"' else inner
        if value is None:
            value = _strip_inline_comment(raw_value)

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
