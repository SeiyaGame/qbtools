"""Rich rendering: pure functions that print, isolated from the pipeline logic."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from rich.console import Console
from rich.table import Table

from .engine import ApplyResult, Plan
from .fields import REGISTRY as FIELDS
from .models import Action, Change, TorrentInfo, TrackerStatus


def render_names(console: Console, title: str, names: Sequence[str]) -> None:
    """Shared list view for a field's known values (`<field> list`)."""
    if not names:
        console.print(f"[yellow]No {title.lower()} found.[/yellow]")
        return
    for n in names:
        console.print(f"  [cyan]{n or '[dim](uncategorised)[/dim]'}[/cyan]")
    console.print(f"[dim]{len(names)} {title.lower()}.[/dim]")


def render_torrents(console: Console, torrents: Sequence[TorrentInfo], *, show_trackers: bool = False, show_special: bool = False) -> None:
    table = Table(header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", max_width=48, no_wrap=True)
    table.add_column("Category", style="cyan")
    table.add_column("Tags", style="magenta")
    table.add_column("State")
    table.add_column("Trk", justify="right")
    for i, t in enumerate(torrents, 1):
        table.add_row(str(i), t.name, t.category or "[dim]-[/dim]", ", ".join(t.tags) or "[dim]-[/dim]", t.state, str(len(t.real_trackers)))
    console.print(table)
    console.print(f"[dim]{len(torrents)} torrent(s).[/dim]")

    if show_trackers:
        for t in torrents:
            console.print(f"\n[bold]{t.name}[/bold]")
            rows = t.trackers if show_special else t.real_trackers
            for tr in rows:
                console.print(f"  [{tr.status.style}]*[/{tr.status.style}] {tr.url}  [dim]({tr.status.label})[/dim]")


def render_hosts(console: Console, torrents: Sequence[TorrentInfo]) -> None:
    """Distinct tracker hosts across the selection - what you'd target to edit."""
    counts: Counter[str] = Counter(host for t in torrents for host in t.hosts)
    if not counts:
        console.print("[yellow]No trackers found in the selection.[/yellow]")
        return
    table = Table(title="Tracker hosts", header_style="bold")
    table.add_column("Host", style="cyan")
    table.add_column("Torrents", justify="right")
    for host, n in counts.most_common():
        table.add_row(host, str(n))
    console.print(table)
    console.print(f"[dim]{len(counts)} distinct host(s) across {len(torrents)} torrent(s).[/dim]")


def render_tracker_urls(console: Console, torrents: Sequence[TorrentInfo]) -> None:
    """Deduplicated summary: each distinct tracker URL once, with usage + health.

    Health is a rollup across every torrent using the URL - green if it works
    anywhere, red if it's broken everywhere, amber otherwise.
    """
    counts: Counter[str] = Counter()
    statuses: dict[str, set[TrackerStatus]] = {}
    for t in torrents:
        for tr in t.real_trackers:
            counts[tr.url] += 1
            statuses.setdefault(tr.url, set()).add(tr.status)
    if not counts:
        console.print("[yellow]No trackers found in the selection.[/yellow]")
        return
    table = Table(title="Tracker URLs", header_style="bold")
    table.add_column("", justify="center")  # health dot
    table.add_column("URL", style="cyan", no_wrap=True)
    table.add_column("Torrents", justify="right")
    for url, n in counts.most_common():
        table.add_row(_health_dot(statuses[url]), url, str(n))
    console.print(table)
    console.print(f"[dim]{len(counts)} distinct URL(s) across {len(torrents)} torrent(s).[/dim]")


def _health_dot(seen: set[TrackerStatus]) -> str:
    """A colour rollup for one URL's status across the torrents that carry it."""
    if TrackerStatus.WORKING in seen:
        style = TrackerStatus.WORKING.style
    elif seen == {TrackerStatus.NOT_WORKING}:
        style = TrackerStatus.NOT_WORKING.style
    else:
        style = TrackerStatus.NOT_CONTACTED.style
    return f"[{style}]*[/{style}]"


def render_plan(console: Console, plan: Plan, *, dry_run: bool) -> None:
    if plan.is_empty:
        console.print(f"[yellow]No matching {plan.field} - nothing to change.[/yellow]")
        return
    table = Table(title=f"Field: {plan.field}", title_style="bold", header_style="bold", show_lines=False)
    table.add_column("Torrent", max_width=40, no_wrap=True)
    table.add_column("", justify="center")  # action glyph
    table.add_column("From / To")
    for torrent, changes in plan.by_torrent().items():
        first = True
        for c in changes:
            label = torrent.name if first else ""
            table.add_row(label, f"[{c.action.style}]{c.action.symbol}[/{c.action.style}]", _change_detail(c))
            first = False
    console.print(table)

    verb = "Would change" if dry_run else "Changing"
    console.print(f"[bold]{verb} {len(plan.changes)} {plan.field} value(s) across {plan.torrent_count} torrent(s).[/bold]")
    if dry_run:
        console.print("[dim]Dry-run - pass --run to apply.[/dim]")


def _change_detail(c: Change) -> str:
    if c.action in (Action.EDIT, Action.SET):
        return f"[dim]{c.old or '(none)'}[/dim]\n[{c.action.style}]{c.new}[/{c.action.style}]"
    if c.action is Action.ADD:
        return f"[{c.action.style}]{c.new}[/{c.action.style}]"
    return f"[dim strike]{c.old}[/dim strike]"  # remove


def render_fields(console: Console) -> None:
    table = Table(title="Fields", header_style="bold", show_lines=False)
    table.add_column("Field", style="cyan")
    table.add_column("Kind", justify="center")
    table.add_column("Actions")
    table.add_column("Description")
    for cls in FIELDS:
        kind = "multi" if cls.multi else "single"
        acts = " ".join(f"[{a.style}]{a}[/{a.style}]" for a in cls.actions)
        table.add_row(cls.name, kind, acts, cls.description)
    console.print(table)


def render_apply(console: Console, result: ApplyResult) -> None:
    console.print(f"[green]Applied {result.applied} change(s).[/green]")
    for change, error in result.failed:
        console.print(f"[red]FAILED[/red] {change.torrent.name}: {error}")
    if result.failed:
        console.print(f"[red]{len(result.failed)} change(s) failed.[/red]")
