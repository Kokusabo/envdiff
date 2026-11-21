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
    if quote == "'":
        # Single quotes are literal: no escapes.
        end = value.find("'", 1)
        return None if end == -1 else value[1:end]

    # Double quotes: \" \\ \n \t \r are escapes; other backslashes are kept.
    escapes = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r"}
    out: list[str] = []
    i = 1
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append(escapes.get(nxt, "\\" + nxt))
            i += 2
            continue
        if ch == '"':
            return "".join(out)
        out.append(ch)
        i += 1
    return None  # no closing quote


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
    seen_lines: dict[str, int] = {}

    for number, raw_line in enumerate(text.lstrip(BOM).splitlines(), start=1):
        parsed = parse_line(raw_line)
        if parsed.kind == "error":
            result.warnings.append(f"line {number}: {parsed.error}, line ignored")
            continue
        if parsed.kind != "assign":
            continue
        if parsed.key in seen_lines:
            result.warnings.append(
                f"line {number}: {parsed.key} already defined on line "
                f"{seen_lines[parsed.key]}, using this value"
            )
        seen_lines[parsed.key] = number
        result.values[parsed.key] = parsed.value
    return result


@dataclass
class Line:
    """One classified line of a .env file.

    kind is "blank", "comment", "assign" (key and value set), or "error"
    (error holds the reason).
    """

    kind: str
    key: str = ""
    value: str = ""
    error: str = ""


def parse_line(raw_line: str) -> Line:
    """Classify and parse a single line of a .env file."""
    line = raw_line.strip().lstrip(BOM)
    if not line:
        return Line("blank")
    if line.startswith("#"):
        return Line("comment")
    if line.startswith("export "):
        line = line[len("export ") :].lstrip()
    if "=" not in line:
        return Line("error", error="no '=' found")
    key, _, raw_value = line.partition("=")
    key = key.strip()
    if not key or " " in key:
        return Line("error", error=f"invalid key {key!r}")
    raw_value = raw_value.strip()
    quoted = _unquote(raw_value)
    value = quoted if quoted is not None else _strip_inline_comment(raw_value)
    return Line("assign", key=key, value=value)


def parse_env(text: str) -> dict[str, str]:
    """Parse the text of a .env file and return only the variables."""
    return parse_env_detailed(text).values


def load_env_detailed(path: str | Path) -> ParseResult:
    """Read a .env file from disk and return values plus warnings."""
    return parse_env_detailed(Path(path).read_text(encoding="utf-8"))


def load_env(path: str | Path) -> dict[str, str]:
    """Read and parse a .env file from disk."""
    return load_env_detailed(path).values
