"""Typed domain models, agnostic of the qBittorrent Web API payloads.

`client.py` parses the raw AttrDicts the API returns into these shapes, so the
rest of the tool (filtering, operations, UI) never touches a raw response dict.
Nothing here does I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from urllib.parse import urlsplit


class TrackerStatus(IntEnum):
    """Health of a tracker, as reported by the Web API (`tracker.status`).

    Each member carries its human label and rich style, so the UI reads them off
    the status instead of hard-coding a code->colour table somewhere else.
    """

    label: str
    style: str

    def __new__(cls, value: int, label: str = "", style: str = "white"):
        member = int.__new__(cls, value)
        member._value_ = value
        member.label = label
        member.style = style
        return member

    DISABLED = 0, "disabled", "dim"  # the DHT / PeX / LSD pseudo-trackers
    NOT_CONTACTED = 1, "not contacted", "yellow"
    WORKING = 2, "working", "green"
    UPDATING = 3, "updating", "cyan"
    NOT_WORKING = 4, "not working", "red"

    @classmethod
    def from_code(cls, code: int | str | None) -> TrackerStatus:
        """Map a raw status code, tolerating anything unexpected."""
        try:
            return cls(int(code))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return cls.NOT_CONTACTED


class TorrentState(StrEnum):
    """A value for the Web API `status_filter` - the server-side bucket used to
    narrow `torrents_info`, not a torrent's live state.

    Only the buckets qBittorrent actually accepts here are declared, so Typer can
    offer them as `--state` choices and an unknown one fails at parse time.
    """

    ALL = "all"
    DOWNLOADING = "downloading"
    SEEDING = "seeding"
    COMPLETED = "completed"
    STOPPED = "stopped"  # "paused" in qBittorrent < 5.0
    ACTIVE = "active"
    INACTIVE = "inactive"
    STALLED = "stalled"
    ERRORED = "errored"


class Action(StrEnum):
    """What a single planned change does to one value of a field.

    Field-agnostic: the same verbs drive trackers, tags, category, ... Carries its
    glyph and colour so the plan table stays declarative.

      SET     replace a single-valued field outright (category, name, save path)
      EDIT    rewrite a value in place (regex/substring replace)
      ADD     append a value to a multi-valued field (trackers, tags)
      REMOVE  drop a matching value from a multi-valued field
    """

    symbol: str
    style: str

    def __new__(cls, value: str, symbol: str = "", style: str = "white"):
        member = str.__new__(cls, value)
        member._value_ = value
        member.symbol = symbol
        member.style = style
        return member

    SET = "set", "=", "cyan"
    EDIT = "edit", "~", "yellow"
    ADD = "add", "+", "green"
    REMOVE = "remove", "-", "red"


@dataclass(frozen=True)
class Tracker:
    """One tracker entry of a torrent."""

    url: str
    status: TrackerStatus = TrackerStatus.NOT_CONTACTED
    tier: int = 0
    message: str = ""
    num_peers: int = -1

    @property
    def host(self) -> str:
        """`urlsplit` hostname, e.g. `tracker.example.org`. Empty for pseudo-entries."""
        return urlsplit(self.url).hostname or ""

    @property
    def is_special(self) -> bool:
        """DHT / PeX / LSD rows (`** [DHT] **`, ...): never real, editable trackers."""
        return self.url.startswith("**") or self.status is TrackerStatus.DISABLED


@dataclass(frozen=True)
class TorrentInfo:
    """A torrent plus its trackers - the unit operations act on."""

    hash: str
    name: str
    category: str = ""
    tags: tuple[str, ...] = ()
    state: str = ""
    save_path: str = ""
    trackers: tuple[Tracker, ...] = ()

    @property
    def real_trackers(self) -> tuple[Tracker, ...]:
        """Editable trackers only - the DHT/PeX/LSD pseudo-rows filtered out."""
        return tuple(t for t in self.trackers if not t.is_special)

    @property
    def hosts(self) -> tuple[str, ...]:
        """Distinct tracker hosts, in first-seen order."""
        return tuple(dict.fromkeys(t.host for t in self.real_trackers if t.host))


@dataclass(frozen=True)
class Change:
    """One planned edit to one value of one field of one torrent - a `Plan` atom.

    `field` is the field's registry name (e.g. "trackers"). `old`/`new` are filled
    per action: EDIT/SET set both, ADD only `new`, REMOVE only `old`.
    """

    torrent: TorrentInfo
    field: str
    action: Action
    old: str = ""
    new: str = ""

    @property
    def is_noop(self) -> bool:
        """An EDIT/SET whose replacement equals the original - nothing to do."""
        return self.action in (Action.EDIT, Action.SET) and self.old == self.new


@dataclass(frozen=True)
class TorrentFilter:
    """Which torrents to act on.

    Split in two on purpose: `api_kwargs()` are the axes qBittorrent filters
    server-side (category, tag, state, explicit hashes); `matches()` is the
    client-side refinement the API can't express (name / tracker substrings).

    `category=None` / `tag=None` mean "don't filter"; the empty string `""` is a
    real qBittorrent filter meaning *uncategorised* / *untagged*.
    """

    category: str | None = None
    tag: str | None = None
    state: TorrentState = TorrentState.ALL
    name_contains: str = ""
    tracker_contains: str = ""
    hashes: tuple[str, ...] = ()

    def api_kwargs(self) -> dict:
        kwargs: dict = {"status_filter": str(self.state)}
        if self.category is not None:
            kwargs["category"] = self.category
        if self.tag is not None:
            kwargs["tag"] = self.tag
        if self.hashes:
            kwargs["torrent_hashes"] = list(self.hashes)
        return kwargs

    def matches(self, torrent: TorrentInfo) -> bool:
        if self.name_contains and self.name_contains.casefold() not in torrent.name.casefold():
            return False
        if self.tracker_contains:
            needle = self.tracker_contains.casefold()
            if not any(needle in tr.url.casefold() for tr in torrent.trackers):
                return False
        return True
