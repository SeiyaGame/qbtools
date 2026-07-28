"""Remove matching values from a multi-valued field (trackers, tags)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import TYPE_CHECKING

from ..models import Action, Change, TorrentInfo
from .base import FieldOperation

if TYPE_CHECKING:
    from ..fields import TorrentField


@dataclass
class RemoveOperation(FieldOperation):
    """Remove every value that matches `match` (substring, or regex)."""

    name = "remove"
    description = "Remove matching values from a multi-valued field."
    action = Action.REMOVE

    match: str
    regex: bool = False
    _pattern: re.Pattern | None = dc_field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._pattern = re.compile(self.match) if self.regex else None

    def _hit(self, value: str) -> bool:
        if self._pattern is not None:
            return self._pattern.search(value) is not None
        return self.match in value

    def changes(self, field: TorrentField, torrent: TorrentInfo) -> list[Change]:
        return [Change(torrent, field.name, Action.REMOVE, v, "") for v in field.values(torrent) if self._hit(v)]
