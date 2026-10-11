"""Report generation — Rich terminal table and JSON export."""

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from radar import PackageHealth


def _format_date(dt: datetime | None) -> str:
    """Format a datetime for human-friendly display.

    Args:
        dt: The datetime to format.

    Returns:
        ``"YYYY-MM-DD"`` or ``"N/A"``.
    """
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d")


def _label_color(label: str) -> str:
    """Map a health label to a Rich colour name.

    Args:
        label: One of ``"Healthy"``, ``"Watch"``, ``"At Risk"``, or other.

    Returns:
        A Rich colour string.
    """
    match label:
        case "Healthy":
            return "green"
        case "Watch":
            return "yellow"
        case "At Risk":
            return "red"
        case _:
            return "dim"


def print_table(results: list[PackageHealth]) -> None:
    """Print a colour-coded Rich table sorted by score (worst first).

    Args:
        results: List of health results to display.
    """
    console = Console()
    sorted_results = sorted(results, key=lambda r: r.score)

    table = Table(
        title="Dependency Radar",
        title_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Package", style="bold")
    table.add_column("Score", justify="center")
    table.add_column("Label", justify="center")
    table.add_column("Last Release", justify="center")
    table.add_column("Last Commit", justify="center")
    table.add_column("Main Concern")

    for result in sorted_results:
        color = _label_color(result.label)
        table.add_row(
            result.name,
            f"[{color}]{result.score}[/{color}]",
            f"[{color}]{result.label}[/{color}]",
            _format_date(result.last_release),
            _format_date(result.last_commit),
            result.main_reason,
        )

    console.print()
    console.print(table)
    console.print()

    # Summary line
    healthy = sum(1 for r in results if r.label == "Healthy")
    watch = sum(1 for r in results if r.label == "Watch")
    at_risk = sum(1 for r in results if r.label == "At Risk")
    unknown = sum(1 for r in results if r.label == "Unknown")

    console.print(
        f"  [green]+ Healthy: {healthy}[/green]  "
        f"[yellow]! Watch: {watch}[/yellow]  "
        f"[red]x At Risk: {at_risk}[/red]  "
        f"[dim]? Unknown: {unknown}[/dim]"
    )
    console.print()


def export_json(results: list[PackageHealth], output_path: str | Path) -> None:
    """Export health results to a JSON file.

    Args:
        results: List of health results to serialise.
        output_path: Destination file path (parent dirs created automatically).
    """
    data = []
    for result in sorted(results, key=lambda r: r.score):
        data.append(
            {
                "name": result.name,
                "version": result.version,
                "score": result.score,
                "label": result.label,
                "last_release": (
                    result.last_release.isoformat() if result.last_release else None
                ),
                "last_commit": (
                    result.last_commit.isoformat() if result.last_commit else None
                ),
                "main_reason": result.main_reason,
            }
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
