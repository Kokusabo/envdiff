"""Command-line interface for envdiff."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from envdiff import __version__
from envdiff.diff import DiffResult, compare
from envdiff.example import make_example
from envdiff.parser import load_env_detailed
from envdiff.redact import display_value
from envdiff.scan import DEFAULT_IGNORED, Usage, scan

app = typer.Typer(
    help="Keep .env files honest: compare them, generate .env.example, and find "
    "variables your code reads but never documents. Secrets are masked.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


class OutputFormat(StrEnum):
    table = "table"
    json = "json"
    github = "github"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"envdiff {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """envdiff root options."""


# ---------------------------------------------------------------- helpers


def _resolve_format(fmt: OutputFormat, as_json: bool) -> OutputFormat:
    return OutputFormat.json if as_json else fmt


def _gh_escape(text: str, prop: bool = False) -> str:
    text = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if prop:
        text = text.replace(":", "%3A").replace(",", "%2C")
    return text


def _gh_annotation(level: str, message: str, file: Path | None = None, line: int | None = None):
    """Print a GitHub Actions workflow command (shows up inline on pull requests)."""
    props = ["title=envdiff"]
    if file is not None:
        props.insert(0, f"file={_gh_escape(file.as_posix(), prop=True)}")
    if line is not None:
        props.insert(1, f"line={line}")
    typer.echo(f"::{level} {','.join(props)}::{_gh_escape(message)}")


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------- compare


def _is_failed(result: DiffResult, strict: bool) -> bool:
    return result.has_errors or (strict and bool(result.empty))


def _json_payload(base: Path, other: Path, result: DiffResult, failed: bool) -> dict:
    return {
        "base": str(base),
        "other": str(other),
        "ok": not failed,
        "missing": result.missing,
        "extra": result.extra,
        "empty": result.empty,
        "changed": result.changed,
    }


def _print_report(
    result: DiffResult,
    base_env: dict[str, str],
    other_env: dict[str, str],
    base_name: str,
    other_name: str,
    show_changed: bool,
) -> None:
    table = Table(title=f"{base_name} vs {other_name}", show_lines=False)
    table.add_column("Key", style="bold")
    table.add_column("Status")
    table.add_column(base_name)
    table.add_column(other_name)

    for key in result.missing:
        table.add_row(key, "[red]missing[/red]", display_value(key, base_env[key]), "-")
    for key in result.extra:
        table.add_row(key, "[red]extra[/red]", "-", display_value(key, other_env[key]))
    for key in result.empty:
        table.add_row(key, "[yellow]empty[/yellow]", display_value(key, base_env[key]), "(empty)")
    if show_changed:
        for key in result.changed:
            table.add_row(
                key,
                "[cyan]changed[/cyan]",
                display_value(key, base_env[key]),
                display_value(key, other_env[key]),
            )

    if table.row_count:
        console.print(table)

    if result.has_issues:
        console.print(
            f"[red]{len(result.missing)} missing[/red], "
            f"[red]{len(result.extra)} extra[/red], "
            f"[yellow]{len(result.empty)} empty[/yellow]"
        )
    else:
        console.print(f"[green]OK[/green]: {other_name} matches {base_name}")
    if show_changed:
        console.print(f"[cyan]{len(result.changed)} changed[/cyan]")


def _print_github(result: DiffResult, base: Path, other: Path, strict: bool) -> None:
    for key in result.missing:
        _gh_annotation("error", f"{key} is missing (it is defined in {base.name})", other)
    for key in result.extra:
        _gh_annotation("error", f"{key} is not defined in {base.name}", other)
    for key in result.empty:
        _gh_annotation("error" if strict else "warning", f"{key} is empty", other)


@app.command(name="compare")
def compare_cmd(
    base: Path = typer.Argument(
        ..., exists=True, dir_okay=False, help="Reference file, e.g. .env.example."
    ),
    others: list[Path] = typer.Argument(
        ..., exists=True, dir_okay=False, help="One or more files to check against BASE."
    ),
    strict: bool = typer.Option(False, "--strict", help="Also fail on empty values."),
    ignore: list[str] = typer.Option(
        [], "--ignore", "-i", help="Key to skip (repeatable). Example: -i DEBUG -i LOG_LEVEL."
    ),
    show_changed: bool = typer.Option(
        False, "--show-changed", help="Also list keys whose values differ (secrets masked)."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show parser warnings: bad lines and duplicate keys."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format.", case_sensitive=False
    ),
    as_json: bool = typer.Option(False, "--json", help="Shortcut for --format json."),
) -> None:
    """Compare each OTHER file against BASE and report differences.

    Exit code 0 when no problems are found in any file, 1 otherwise.
    """
    fmt = _resolve_format(fmt, as_json)
    ignored = set(ignore)

    def load(path: Path) -> dict[str, str]:
        parsed = load_env_detailed(path)
        if verbose:
            for warning in parsed.warnings:
                err_console.print(f"[yellow]warning[/yellow] {path.name}: {warning}")
        return {k: v for k, v in parsed.values.items() if k not in ignored}

    base_env = load(base)
    payloads: list[dict] = []
    any_failed = False

    for other in others:
        other_env = load(other)
        result = compare(base_env, other_env)
        failed = _is_failed(result, strict)
        any_failed = any_failed or failed

        if fmt is OutputFormat.json:
            payloads.append(_json_payload(base, other, result, failed))
        elif fmt is OutputFormat.github:
            _print_github(result, base, other, strict)
        else:
            _print_report(result, base_env, other_env, base.name, other.name, show_changed)

    if fmt is OutputFormat.json:
        # One file keeps the single-object shape; several files give a list.
        data = payloads[0] if len(payloads) == 1 else payloads
        typer.echo(json.dumps(data, indent=2))

    raise typer.Exit(code=1 if any_failed else 0)


# ---------------------------------------------------------------- example


@app.command(name="example")
def example_cmd(
    source: Path = typer.Argument(
        ..., exists=True, dir_okay=False, help="Real env file to turn into a template, e.g. .env."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write to this file instead of printing."
    ),
    keep_values: bool = typer.Option(
        False, "--keep-values", help="Keep values of non-secret keys (secrets are still blanked)."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite OUTPUT if it already exists."),
) -> None:
    """Generate a .env.example from a real env file, with values removed.

    Comments and blank lines are kept. Secrets are never copied.
    """
    text = make_example(source.read_text(encoding="utf-8"), keep_values=keep_values)
    if output is None:
        typer.echo(text, nl=False)
        return
    if output.exists() and not force:
        err_console.print(f"[red]error[/red]: {output} already exists, use --force to overwrite")
        raise typer.Exit(code=2)
    output.write_text(text, encoding="utf-8")
    count = sum(1 for line in text.splitlines() if line and not line.lstrip().startswith("#"))
    err_console.print(f"[green]Wrote[/green] {output} ({count} variables)")


# ---------------------------------------------------------------- scan


def _where(usages: list[Usage]) -> str:
    first = usages[0]
    more = f" (+{len(usages) - 1} more)" if len(usages) > 1 else ""
    return f"{_display_path(first.path)}:{first.line}{more}"


@app.command(name="scan")
def scan_cmd(
    paths: list[Path] | None = typer.Argument(
        None, exists=True, help="Files or folders to scan. Default: current folder."
    ),
    against: Path = typer.Option(
        Path(".env.example"),
        "--against",
        "-a",
        exists=True,
        dir_okay=False,
        help="The env file that documents the variables.",
    ),
    ignore: list[str] = typer.Option(
        [], "--ignore", "-i", help="Variable to skip (repeatable)."
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Also fail on documented variables that the code never reads."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format.", case_sensitive=False
    ),
    as_json: bool = typer.Option(False, "--json", help="Shortcut for --format json."),
) -> None:
    """Find env variables your code reads that are missing from .env.example.

    Understands Python, JavaScript/TypeScript (process.env, import.meta.env), Go,
    Ruby, Rust, and PHP. Exit code 1 when undocumented variables are found.
    """
    fmt = _resolve_format(fmt, as_json)
    ignored = set(ignore) | DEFAULT_IGNORED
    usages = scan(paths or [Path(".")])
    documented = set(load_env_detailed(against).values)

    undocumented = {n: u for n, u in usages.items() if n not in documented and n not in ignored}
    unused = sorted(n for n in documented if n not in usages and n not in ignored)
    failed = bool(undocumented) or (strict and bool(unused))

    if fmt is OutputFormat.json:
        payload = {
            "against": str(against),
            "ok": not failed,
            "used": sorted(usages),
            "undocumented": {
                name: [{"path": _display_path(u.path), "line": u.line} for u in found]
                for name, found in undocumented.items()
            },
            "unused": unused,
        }
        typer.echo(json.dumps(payload, indent=2))
    elif fmt is OutputFormat.github:
        for name, found in undocumented.items():
            for usage in found:
                _gh_annotation(
                    "error",
                    f"{name} is read here but not documented in {against.name}",
                    Path(_display_path(usage.path)),
                    usage.line,
                )
        for name in unused:
            _gh_annotation(
                "error" if strict else "warning",
                f"{name} is documented but never read by the scanned code",
                against,
            )
    else:
        table = Table(title=f"code vs {against.name}")
        table.add_column("Variable", style="bold")
        table.add_column("Status")
        table.add_column("Where")
        for name, found in undocumented.items():
            table.add_row(name, "[red]undocumented[/red]", _where(found))
        for name in unused:
            table.add_row(name, "[yellow]unused[/yellow]", _display_path(against))
        if table.row_count:
            console.print(table)
        if undocumented or unused:
            console.print(
                f"[red]{len(undocumented)} undocumented[/red], "
                f"[yellow]{len(unused)} unused[/yellow] "
                f"({len(usages)} variables read by the code)"
            )
        else:
            console.print(
                f"[green]OK[/green]: all {len(usages)} variables read by the code "
                f"are documented in {against.name}"
            )

    raise typer.Exit(code=1 if failed else 0)


if __name__ == "__main__":
    app()
