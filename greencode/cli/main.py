"""
greencode/cli/main.py
━━━━━━━━━━━━━━━━━━━━
CLI entrypoint.  Usage:

    greencode measure
    greencode measure --command "python -m pytest tests/"
    greencode badge
    greencode report
    greencode history
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    _rich = True
except ImportError:
    _rich = False

from .measure import measure, load_latest, load_history, compare, GRADE_LABELS
from .badge import generate, save, readme_snippet, generate_all_grades

console = Console() if _rich else None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print(msg: str, style: str = ""):
    if _rich and console:
        console.print(msg, style=style)
    else:
        print(msg)


def _grade_color(g: str) -> str:
    return {"green": "green", "yellow": "yellow", "red": "red"}.get(g, "white")


def _render_result(result: dict, delta: dict | None = None):
    """Pretty-print a measurement result."""
    if not _rich:
        print(json.dumps(result, indent=2))
        return

    meta  = GRADE_LABELS[result["grade"]]
    color = _grade_color(result["grade"])

    lines = [
        f"[bold white]Project:[/]  {result['project']}",
        f"[bold white]Commit:[/]   {result['commit']}  ({result['branch']})",
        f"[bold white]CO₂:[/]      [{color}]{meta['emoji']} {result['grams_co2']:.4f} g[/]  ({result['kg_co2']:.8f} kg)",
        f"[bold white]Grade:[/]    [{color}]{result['grade'].upper()} — {meta['label']}[/]",
        f"[bold white]Method:[/]   {result['note']}",
    ]

    if delta and delta["direction"] != "first":
        arrow = "▲" if delta["direction"] == "up" else "▼"
        dc    = "red" if delta["direction"] == "up" else "green"
        lines.append(
            f"[bold white]vs prev:[/]  [{dc}]{arrow} {abs(delta['delta_grams']):.4f} g "
            f"({delta['delta_pct']:+.1f}%)[/]"
        )

    console.print(Panel(
        "\n".join(lines),
        title=f"[bold {color}]GreenCode Measurement[/]",
        border_style=color,
        padding=(1, 2),
    ))


# ── Commands ──────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("0.1.0", prog_name="greencode")
def cli():
    """🌿 GreenCode — measure and track your code's carbon footprint."""
    pass


@cli.command()
@click.option("--path",    "-p", default=".", help="Project path to measure")
@click.option("--command", "-c", default=None, help="Command to run (default: pytest)")
@click.option("--country", default="DEU", help="ISO country code for emission factors")
@click.option("--json",    "as_json", is_flag=True, help="Output raw JSON")
@click.option("--no-save", is_flag=True, help="Don't save to history")
def measure_cmd(path, command, country, as_json, no_save):
    """Measure CO₂ emissions while running your tests."""
    cmd = command.split() if command else None

    _print("[dim]⚡ Running measurement...[/dim]")

    result  = measure(path=path, command=cmd, country_iso=country, save=not no_save)
    history = load_history()
    prev    = history[-2] if len(history) >= 2 else None
    delta   = compare(result, prev)

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        _render_result(result, delta)

        # Auto-save badge
        svg  = generate(result["grams_co2"], result["grade"])
        path_ = save(svg)
        _print(f"\n[dim]Badge saved → {path_}[/dim]")
        _print(f"[dim]Add to README:[/dim]")

        owner = "your-username"
        repo  = result["project"]
        _print(f"[green]{readme_snippet(owner, repo)}[/green]")


@cli.command()
@click.option("--owner", default="your-username", help="GitHub owner/org")
@click.option("--repo",  default=None, help="Repo name (default: current dir name)")
@click.option("--output", "-o", default=None, help="Output SVG path")
def badge_cmd(owner, repo, output):
    """Generate the SVG badge from latest measurement."""
    result = load_latest()

    if not result:
        _print("[red]No measurement found. Run `greencode measure` first.[/red]")
        sys.exit(1)

    svg   = generate(result["grams_co2"], result["grade"])
    path_ = save(svg, Path(output) if output else None)

    _print(f"[green]✓ Badge saved → {path_}[/green]")

    repo_name = repo or result["project"]
    snippet   = readme_snippet(owner, repo_name)
    _print(f"\n[bold]Add this to your README.md:[/bold]")
    _print(f"[yellow]{snippet}[/yellow]")


@cli.command()
@click.option("--limit", "-n", default=10, help="Number of recent entries")
@click.option("--json",  "as_json", is_flag=True)
def history_cmd(limit, as_json):
    """Show measurement history."""
    hist = load_history()[-limit:]

    if not hist:
        _print("[dim]No history yet. Run `greencode measure` first.[/dim]")
        return

    if as_json:
        print(json.dumps(hist, indent=2))
        return

    if _rich:
        t = Table(title="GreenCode History", box=box.SIMPLE_HEAVY,
                  header_style="bold dim")
        t.add_column("Date",    style="dim",   width=12)
        t.add_column("Commit",  style="dim",   width=8)
        t.add_column("Branch",  style="dim",   width=12)
        t.add_column("CO₂ (g)", justify="right")
        t.add_column("Grade",   justify="center")

        for r in reversed(hist):
            g     = r["grade"]
            color = _grade_color(g)
            meta  = GRADE_LABELS[g]
            date  = r["timestamp"][:10]
            t.add_row(
                date,
                r["commit"],
                r["branch"],
                f"[{color}]{r['grams_co2']:.4f}[/]",
                f"[{color}]{meta['emoji']} {g}[/]",
            )
        console.print(t)
    else:
        for r in hist:
            print(f"{r['timestamp'][:10]}  {r['commit']}  {r['grams_co2']:.4f}g  {r['grade']}")


@cli.command()
def samples():
    """Generate sample badges for all three grade levels (for docs/testing)."""
    badges = generate_all_grades()
    _print("[bold]Sample badges generated:[/bold]\n")
    for grade_name, svg in badges.items():
        meta  = GRADE_LABELS[grade_name]
        path_ = save(svg, Path(f".greencode/badge-{grade_name}.svg"))
        _print(f"  {meta['emoji']} [bold]{grade_name}[/bold] → {path_}")


@cli.command()
@click.option("--output", "-o", default=None, help="Output HTML path")
@click.option("--json",   "as_json", is_flag=True, help="Output JSON instead of HTML")
def report(output, as_json):
    """Generate HTML dashboard or JSON report from history."""
    from .report import save_html_report, save_json_report

    hist = load_history()
    if not hist:
        _print("[red]No history yet. Run `greencode measure` first.[/red]")
        return

    if as_json:
        path_ = save_json_report(output)
        _print(f"[green]✓ JSON report → {path_}[/green]")
    else:
        path_ = save_html_report(output)
        _print(f"[green]✓ Dashboard → {path_}[/green]")
        _print("[dim]Open in browser: open .greencode/dashboard.html[/dim]")


@cli.command()
def pr_comment():
    """Print a GitHub PR comment with the latest measurement."""
    from .report import generate_pr_comment
    hist = load_history()
    if not hist:
        _print("[red]No history. Run `greencode measure` first.[/red]")
        return
    prev = hist[-2] if len(hist) >= 2 else None
    print(generate_pr_comment(hist[-1], prev))


if __name__ == "__main__":
    cli()
