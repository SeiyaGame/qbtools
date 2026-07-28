"""The planner/applier that ties an operation + a field to the client.

Dry-run is the default and the safe path: `plan()` computes every change purely
from the fetched torrents (no writes); `apply()` is the only thing that mutates,
and only what the very same plan described. So what you preview is exactly what
runs. The engine stays field-agnostic: it delegates the actual write to the field.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .client import QbitClient
from .errors import ApiError
from .fields import TorrentField
from .models import Change, TorrentInfo
from .operations import FieldOperation


@dataclass(frozen=True)
class Plan:
    """The set of changes an operation would make to one field across torrents."""

    field: str
    changes: tuple[Change, ...]

    @property
    def is_empty(self) -> bool:
        return not self.changes

    @property
    def torrent_count(self) -> int:
        return len({c.torrent.hash for c in self.changes})

    def by_torrent(self) -> dict[TorrentInfo, list[Change]]:
        """Changes grouped per torrent, preserving discovery order."""
        grouped: dict[TorrentInfo, list[Change]] = defaultdict(list)
        for change in self.changes:
            grouped[change.torrent].append(change)
        return grouped


@dataclass(frozen=True)
class ApplyResult:
    applied: int
    failed: tuple[tuple[Change, str], ...] = ()


class Engine:
    """Runs one operation over a field for a set of torrents: plan, then apply."""

    def __init__(self, client: QbitClient):
        self.client = client

    def plan(self, operation: FieldOperation, field: TorrentField, torrents: list[TorrentInfo]) -> Plan:
        changes: list[Change] = []
        for torrent in torrents:
            changes.extend(c for c in operation.changes(field, torrent) if not c.is_noop)
        return Plan(field=field.name, changes=tuple(changes))

    def apply(self, plan: Plan, field: TorrentField) -> ApplyResult:
        """Push every change to qBittorrent, collecting per-change failures."""
        applied = 0
        failed: list[tuple[Change, str]] = []
        for change in plan.changes:
            try:
                field.apply(self.client, change)
                applied += 1
            except ApiError as exc:
                failed.append((change, str(exc)))
        return ApplyResult(applied=applied, failed=tuple(failed))
