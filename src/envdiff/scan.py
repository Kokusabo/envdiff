"""Find environment variables referenced in source code."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

_NAME = r"([A-Za-z_][A-Za-z0-9_]*)"
_Q = r"""['"`]"""

PATTERNS: tuple[re.Pattern[str], ...] = (
    # Python / PHP: os.getenv("X"), getenv("X"), os.environ.get("X"), environ.get("X")
    re.compile(rf"\b(?:os\.)?(?:environ\.get|getenv)\(\s*{_Q}{_NAME}{_Q}"),
    # Python: os.environ["X"], environ["X"]
    re.compile(rf"\b(?:os\.)?environ\[\s*{_Q}{_NAME}{_Q}\s*\]"),
    # JavaScript / TypeScript: process.env.X, process.env["X"], import.meta.env.X
    re.compile(rf"\bprocess\.env\.{_NAME}"),
    re.compile(rf"\bprocess\.env\[\s*{_Q}{_NAME}{_Q}\s*\]"),
    re.compile(rf"\bimport\.meta\.env\.{_NAME}"),
    # Go: os.Getenv("X"), os.LookupEnv("X")
    re.compile(rf"\bos\.(?:Getenv|LookupEnv)\(\s*{_Q}{_NAME}{_Q}"),
    # Ruby: ENV["X"], ENV.fetch("X")
    re.compile(rf"\bENV(?:\.fetch\(\s*|\[\s*){_Q}{_NAME}{_Q}"),
    # Rust: env::var("X"), std::env::var_os("X")
    re.compile(rf"\benv::var(?:_os)?\(\s*{_Q}{_NAME}{_Q}"),
)

SOURCE_SUFFIXES = frozenset(
    {
        ".py", ".pyi",
        ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".vue", ".svelte", ".astro",
        ".go", ".rb", ".rs", ".php",
    }
)

SKIP_DIRS = frozenset(
    {
        ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", "__pycache__",
        "dist", "build", ".next", ".nuxt", ".svelte-kit", "target", "vendor",
        ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "coverage",
    }
)

# Names that are set by the runtime or the build tool, not by the project's .env.
DEFAULT_IGNORED = frozenset(
    {
        "PATH", "HOME", "USER", "PWD", "SHELL", "TERM", "LANG", "TZ", "CI", "NODE_ENV",
        # Vite built-ins (import.meta.env.*)
        "MODE", "DEV", "PROD", "SSR", "BASE_URL",
    }
)

MAX_FILE_BYTES = 1_000_000


@dataclass(frozen=True)
class Usage:
    """One place where an environment variable is read."""

    name: str
    path: Path
    line: int


def iter_source_files(paths: Iterable[Path]) -> Iterator[Path]:
    """Yield source files under `paths`, skipping dependency and build folders."""
    for root in paths:
        if root.is_file():
            if root.suffix in SOURCE_SUFFIXES:
                yield root
            continue
        for path in sorted(root.rglob("*")):
            if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
                continue
            if path.is_file() and path.suffix in SOURCE_SUFFIXES:
                yield path


def find_usages_in_text(text: str, path: Path) -> list[Usage]:
    """Return every environment variable read found in `text`."""
    usages: list[Usage] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern in PATTERNS:
            for match in pattern.finditer(line):
                usages.append(Usage(match.group(1), path, number))
    return usages


def scan(paths: Iterable[Path]) -> dict[str, list[Usage]]:
    """Map each variable name to where it is used, in first-seen order."""
    found: dict[str, list[Usage]] = {}
    for path in iter_source_files(paths):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for usage in find_usages_in_text(text, path):
            found.setdefault(usage.name, []).append(usage)
    return found
