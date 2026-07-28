"""Rewrite matching values of any field - the core "edit" operation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import TYPE_CHECKING

from ..models import Action, Change, TorrentInfo
from .base import TrackerOperation

if TYPE_CHECKING:
    from ..fields import TorrentField


@dataclass
class ReplaceOperation(TrackerOperation):
    """Replace `match` with `to` in every value of the field it occurs in.

    Plain substring by default (`old.host` -> `new.host`); with `regex=True`,
    `match` is a Python regex and `to` may reference groups (`\\1`). Works on any
    field: a tracker URL, a tag, a category string, ...
    """

    name = "replace"
    description = "Rewrite matching values (substring, or regex with --regex)."
    action = Action.EDIT

    match: str
    to: str
    regex: bool = False
    _pattern: re.Pattern | None = dc_field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._pattern = re.compile(self.match) if self.regex else None

    def _rewrite(self, value: str) -> str | None:
        """The rewritten value, or None if `match` doesn't apply to it."""
        if self._pattern is not None:
            new, n = self._pattern.subn(self.to, value)
            return new if n else None
        return value.replace(self.match, self.to) if self.match in value else None

    def changes(self, field: TorrentField, torrent: TorrentInfo) -> list[Change]:
        out: list[Change] = []
        for value in field.values(torrent):
            new_value = self._rewrite(value)
            if new_value is not None and new_value != value:
                out.append(Change(torrent, field.name, Action.EDIT, value, new_value))
        return out
