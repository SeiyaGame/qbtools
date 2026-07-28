"""Set a single-valued field outright (category, name, save path)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..models import Action, Change, TorrentInfo
from .base import FieldOperation

if TYPE_CHECKING:
    from ..fields import TorrentField


@dataclass
class SetOperation(FieldOperation):
    """Set the field to `value`, skipping torrents that already hold it."""

    name = "set"
    description = "Set a single-valued field to a fixed value."
    action = Action.SET

    value: str

    def changes(self, field: TorrentField, torrent: TorrentInfo) -> list[Change]:
        current = field.values(torrent)
        old = current[0] if current else ""
        if old == self.value:
            return []
        return [Change(torrent, field.name, Action.SET, old, self.value)]
