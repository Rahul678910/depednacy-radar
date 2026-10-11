"""Typer CLI entry point for Dependency Radar."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from radar import __version__
from radar.fetchers import fetch_all_package_data
from radar.parsers import parse_package_json
from radar.report import export_json, print_table
from radar.scoring import calculate_health

app = typer.Typer(
    name="radar",
    help="Dependency Radar -- Score the health of your project's dependencies.",
    add_completion=False,
)
console = Console()


@app.command()
def scan(
    path: Path = typer.Argument(
        ...,
        help="Path to the package.json file to scan.",
        exists=True,
        readable=True,
    ),
    json_output: Optional[Path] = typer.Option(
        None,
        "--json",
        help="Export results to a JSON file.",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Skip the local cache and fetch fresh data.",
    ),
    fail_under: Optional[int] = typer.Option(
        None,
        "--fail-under",
        help="Exit with code 1 if any package scores below this threshold (CI mode).",
    ),
) -> None:
    """Scan a package.json file and score each dependency's health."""
    console.print(f"\n[bold cyan]Dependency Radar v{__version__}[/bold cyan]")
    console.print(f"  Scanning: [bold]{path}[/bold]\n")

    # ── Parse ────────────────────────────────────────────────────────────
    try:
        packages = parse_package_json(path)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    if not packages:
        console.print("[yellow]No dependencies found in the file.[/yellow]")
        raise typer.Exit(code=0)

    console.print(
        f"  Found [bold]{len(packages)}[/bold] dependencies. Fetching metadata...\n"
    )

    # ── Fetch ────────────────────────────────────────────────────────────
    use_cache = not no_cache
    all_data = fetch_all_package_data(packages, use_cache=use_cache)

    # ── Score ────────────────────────────────────────────────────────────
    results = [
        calculate_health(pkg, npm_data, github_data)
        for pkg, npm_data, github_data in all_data
    ]

    # ── Report ───────────────────────────────────────────────────────────
    print_table(results)

    if json_output:
        export_json(results, json_output)
        console.print(f"  [dim]Results exported to {json_output}[/dim]\n")

    # ── CI fail-under gate ───────────────────────────────────────────────
    if fail_under is not None:
        failing = [r for r in results if r.score < fail_under]
        if failing:
            console.print(
                f"[red]x {len(failing)} package(s) scored below {fail_under}.[/red]\n"
            )
            raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Show the Dependency Radar version."""
    console.print(f"Dependency Radar v{__version__}")


if __name__ == "__main__":
    app()
