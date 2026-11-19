"""Command-line interface for envdiff."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from envdiff import __version__
from envdiff.diff import compare
from envdiff.parser import load_env
from envdiff.redact import display_value

app = typer.Typer(
    help="Compare .env files: find missing, extra, and empty variables. Secrets are masked.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


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


@app.command(name="compare")
def compare_cmd(
    base: Path = typer.Argument(
        ..., exists=True, dir_okay=False, help="Reference file, e.g. .env.example."
    ),
    other: Path = typer.Argument(
        ..., exists=True, dir_okay=False, help="File to check against the reference."
    ),
    strict: bool = typer.Option(False, "--strict", help="Also fail on empty values."),
    ignore: list[str] = typer.Option(
        [], "--ignore", "-i", help="Key to skip (repeatable). Example: -i DEBUG -i LOG_LEVEL."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON (no values)."),
) -> None:
    """Compare OTHER against BASE and report differences.

    Exit code 0 when no problems are found, 1 otherwise.
    """
    ignored = set(ignore)
    base_env = {k: v for k, v in load_env(base).items() if k not in ignored}
    other_env = {k: v for k, v in load_env(other).items() if k not in ignored}
    result = compare(base_env, other_env)
    failed = result.has_errors or (strict and bool(result.empty))

    if as_json:
        payload = {
            "base": str(base),
            "other": str(other),
            "ok": not failed,
            "missing": result.missing,
            "extra": result.extra,
            "empty": result.empty,
        }
        typer.echo(json.dumps(payload, indent=2))
        raise typer.Exit(code=1 if failed else 0)

    table = Table(title=f"{base.name} vs {other.name}", show_lines=False)
    table.add_column("Key", style="bold")
    table.add_column("Status")
    table.add_column(f"{base.name}")
    table.add_column(f"{other.name}")

    for key in result.missing:
        table.add_row(key, "[red]missing[/red]", display_value(key, base_env[key]), "-")
    for key in result.extra:
        table.add_row(key, "[red]extra[/red]", "-", display_value(key, other_env[key]))
    for key in result.empty:
        table.add_row(key, "[yellow]empty[/yellow]", display_value(key, base_env[key]), "(empty)")

    if result.has_issues:
        console.print(table)
        console.print(
            f"[red]{len(result.missing)} missing[/red], "
            f"[red]{len(result.extra)} extra[/red], "
            f"[yellow]{len(result.empty)} empty[/yellow]"
        )
    else:
        console.print(f"[green]OK[/green]: {other.name} matches {base.name}")

    raise typer.Exit(code=1 if failed else 0)


if __name__ == "__main__":
    app()
