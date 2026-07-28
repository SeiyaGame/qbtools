"""The save-path field: single-valued, set/edit (moves the data on disk)."""

from __future__ import annotations

from ..client import QbitClient
from ..models import Action, Change, TorrentInfo
from .base import TorrentField


class SavePathField(TorrentField):
    name = "savepath"
    description = "On-disk save location (setting it moves the files)."
    multi = False
    actions = (Action.SET, Action.EDIT)

    def values(self, torrent: TorrentInfo) -> tuple[str, ...]:
        return (torrent.save_path,)

    def apply(self, client: QbitClient, change: Change) -> None:
        client.set_location(change.torrent.hash, change.new)
