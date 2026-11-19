"""Command-line interface for envdiff."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from envdiff import __version__
from envdiff.diff import DiffResult, compare
from envdiff.parser import load_env_detailed
from envdiff.redact import display_value

app = typer.Typer(
    help="Compare .env files: find missing, extra, and empty variables. Secrets are masked.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


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
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON (no values)."),
) -> None:
    """Compare each OTHER file against BASE and report differences.

    Exit code 0 when no problems are found in any file, 1 otherwise.
    """
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

        if as_json:
            payloads.append(_json_payload(base, other, result, failed))
        else:
            _print_report(result, base_env, other_env, base.name, other.name, show_changed)

    if as_json:
        # One file keeps the single-object shape; several files give a list.
        data = payloads[0] if len(payloads) == 1 else payloads
        typer.echo(json.dumps(data, indent=2))

    raise typer.Exit(code=1 if any_failed else 0)


if __name__ == "__main__":
    app()
