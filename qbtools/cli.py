"""Command-line interface (Typer).

The write surface is noun-verb: every editable **field** is a command group and
every **operation** it supports is a verb under it, so the target reads left to
right - `qbt.py tags remove obsolete`, `qbt.py category set Torr9`,
`qbt.py trackers replace old new`. Both come from registries (`fields/`,
`operations/`): the groups are built by looping over the field registry, and a
group only exposes the operations its field declares, so an unsupported
combination can't even be typed.

The selection vocabulary (`--category/--tag/--state/--name/--tracker/--hash`) is
declared once, in `_FILTER_PARAMS`, and injected into every command by the
`@with_filters` decorator, which hands the command a ready-built `TorrentFilter`.
So a command's own signature only carries what is unique to it.

Read commands never change anything; write commands are a dry-run that prints
their plan and stop unless `--run` is passed.
"""

from __future__ import annotations

import functools
import inspect

import typer
from rich.console import Console

from . import ui
from .client import QbitClient
from .config import load_settings
from .engine import Engine
from .errors import TrackerToolError
from .fields import REGISTRY as FIELDS
from .fields import TorrentField
from .models import Action, TorrentFilter, TorrentInfo, TorrentState
from .operations import FieldOperation
from .operations.add import AddOperation
from .operations.remove import RemoveOperation
from .operations.replace import ReplaceOperation
from .operations.set import SetOperation

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Bulk-edit qBittorrent torrents (trackers, tags, category, ...), filtered by category / tag / state.")
console = Console()

# -- shared options -----------------------------------------------------------
_RUN = typer.Option(False, "--run", help="Actually apply the changes (default: dry-run, plan only).")
_REGEX = typer.Option(False, "--regex", help="Treat the match pattern as a Python regex.")

# The selection filter - declared once, injected everywhere by @with_filters.
_KW = inspect.Parameter.KEYWORD_ONLY
_FILTER_PARAMS = [
    inspect.Parameter("category", _KW, annotation=str | None, default=typer.Option(None, "--category", "-c", help="Category filter. Pass '' for uncategorised. Omit = any.")),
    inspect.Parameter("tag", _KW, annotation=str | None, default=typer.Option(None, "--tag", "-t", help="Tag filter. Pass '' for untagged. Omit = any.")),
    inspect.Parameter("state", _KW, annotation=TorrentState, default=typer.Option(TorrentState.ALL, "--state", "-s", help="Server-side state bucket.")),
    inspect.Parameter("name", _KW, annotation=str, default=typer.Option("", "--name", "-n", help="Only torrents whose name contains this (case-insensitive).")),
    inspect.Parameter("tracker", _KW, annotation=str, default=typer.Option("", "--tracker", help="Only torrents that have a tracker URL containing this.")),
    inspect.Parameter("hashes", _KW, annotation=list[str] | None, default=typer.Option(None, "--hash", "-H", help="Restrict to these torrent hashes (repeatable).")),
]


def with_filters(func):
    """Inject the shared selection options and pass the command a `TorrentFilter`.

    The decorated command declares `*, filter: TorrentFilter` and never repeats the
    filter options: this appends them to its public signature (what Typer reads),
    collects them at call time and builds the `TorrentFilter` once.
    """

    @functools.wraps(func)
    def wrapper(*args, category=None, tag=None, state=TorrentState.ALL, name="", tracker="", hashes=None, **kwargs):
        filter = TorrentFilter(category=category, tag=tag, state=state, name_contains=name, tracker_contains=tracker, hashes=tuple(hashes or ()))
        return func(*args, filter=filter, **kwargs)

    sig = inspect.signature(func)
    own = [p for n, p in sig.parameters.items() if n != "filter"]
    wrapper.__signature__ = sig.replace(parameters=[*own, *_FILTER_PARAMS])
    return wrapper


class Session:
    """A lazily-connected qBittorrent session driving the read/edit pipeline.

    The connection opens on first use, so connection-free commands (`fields`) never
    touch the network. `run()` turns one operation + field over a selection into a
    rendered, optionally-applied plan - the single write path.
    """

    def __init__(self, console: Console):
        self.console = console
        self._client: QbitClient | None = None

    @property
    def client(self) -> QbitClient:
        if self._client is not None:
            return self._client
        config = load_settings().require()
        try:
            client = QbitClient(config).connect()
        except TrackerToolError as exc:
            raise SystemExit(f"qBittorrent: {exc}")
        self._client = client
        return client

    def torrents(self, filter: TorrentFilter) -> list[TorrentInfo]:
        return self.client.torrents(filter)

    def run(self, operation: FieldOperation, field: TorrentField, filter: TorrentFilter, *, apply: bool) -> None:
        torrents = self.torrents(filter)
        if not torrents:
            self.console.print("[yellow]No torrents matched the filters.[/yellow]")
            return
        engine = Engine(self.client)
        plan = engine.plan(operation, field, torrents)
        ui.render_plan(self.console, plan, dry_run=not apply)
        if apply and not plan.is_empty:
            ui.render_apply(self.console, engine.apply(plan, field))


session = Session(console)


@app.command("ping")
def ping() -> None:
    """Check the connection and print the qBittorrent versions."""
    client = session.client
    app_v, api_v = client.versions()
    console.print(f"[green]Connected[/green] to {client.config.base_url} - qBittorrent [bold]{app_v}[/bold] (Web API {api_v}).")


@app.command("fields")
def list_fields() -> None:
    """List the editable fields and which operations apply to each."""
    ui.render_fields(console)


@app.command("list")
@with_filters
def list_torrents(
    trackers: bool = typer.Option(False, "--trackers", help="Also print each torrent's tracker URLs."),
    all: bool = typer.Option(False, "--all", help="Include the DHT/PeX/LSD pseudo-trackers (implies --trackers)."),
    *,
    filter: TorrentFilter,
) -> None:
    """List the torrents that match the filters."""
    ui.render_torrents(console, session.torrents(filter), show_trackers=trackers or all, show_special=all)


@app.command("hosts")
@with_filters
def list_hosts(*, filter: TorrentFilter) -> None:
    """Show the distinct tracker hosts across the selection (what you'd edit)."""
    ui.render_hosts(console, session.torrents(filter))


@app.command("urls")
@with_filters
def list_urls(*, filter: TorrentFilter) -> None:
    """Deduplicated summary of every distinct tracker URL and how many torrents use it."""
    ui.render_tracker_urls(console, session.torrents(filter))


# -- per-field command groups (dry-run unless --run) --------------------------
def _field_app(field: TorrentField) -> typer.Typer:
    """Build one field's command group, exposing only the operations it supports.

    A closure per field (capturing `field`) shares the verb definitions instead of
    duplicating them - mirroring how the sibling `downloader` builds one group per
    service. So `qbt.py <field> <verb>` is generated straight from the registries.
    """
    group = typer.Typer(no_args_is_help=True, help=field.description)

    if Action.EDIT in field.actions:
        @group.command("replace")
        @with_filters
        def replace(
            match: str = typer.Argument(..., help="Substring (or regex with --regex) to find in the values."),
            to: str = typer.Argument(..., help="Replacement. With --regex may reference groups (\\1)."),
            regex: bool = _REGEX,
            run: bool = _RUN,
            *,
            filter: TorrentFilter,
        ) -> None:
            """Rewrite matching values."""
            session.run(ReplaceOperation(match=match, to=to, regex=regex), field, filter, apply=run)

    if Action.ADD in field.actions:
        @group.command("add")
        @with_filters
        def add(value: str = typer.Argument(..., help="Value to add."), run: bool = _RUN, *, filter: TorrentFilter) -> None:
            """Add a value (skips torrents that already have it)."""
            session.run(AddOperation(value=value), field, filter, apply=run)

    if Action.REMOVE in field.actions:
        @group.command("remove")
        @with_filters
        def remove(
            match: str = typer.Argument(..., help="Substring (or regex with --regex) identifying values to remove."),
            regex: bool = _REGEX,
            run: bool = _RUN,
            *,
            filter: TorrentFilter,
        ) -> None:
            """Remove matching values."""
            session.run(RemoveOperation(match=match, regex=regex), field, filter, apply=run)

    if Action.SET in field.actions:
        @group.command("set")
        @with_filters
        def set_value(value: str = typer.Argument(..., help="The value to set."), run: bool = _RUN, *, filter: TorrentFilter) -> None:
            """Set the field outright."""
            session.run(SetOperation(value=value), field, filter, apply=run)

    if field.lists_values:
        @group.command("list")
        def list_known() -> None:
            """List the values qBittorrent already knows for this field."""
            ui.render_names(console, field.name.capitalize(), field.known_values(session.client))

    return group


for _cls in FIELDS:
    app.add_typer(_field_app(_cls()), name=_cls.name)


if __name__ == "__main__":
    app()
