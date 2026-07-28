"""Add a value to a multi-valued field (a tracker URL, a tag)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..models import Action, Change, TorrentInfo
from .base import TrackerOperation

if TYPE_CHECKING:
    from ..fields import TorrentField


@dataclass
class AddOperation(TrackerOperation):
    """Add `value` to the field, skipping torrents that already have it."""

    name = "add"
    description = "Add a value to a multi-valued field (skips duplicates)."
    action = Action.ADD

    value: str

    def changes(self, field: TorrentField, torrent: TorrentInfo) -> list[Change]:
        if self.value in field.values(torrent):
            return []
        return [Change(torrent, field.name, Action.ADD, "", self.value)]
