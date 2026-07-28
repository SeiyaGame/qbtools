"""The display-name field: single-valued, set/edit (renames in qBittorrent only)."""

from __future__ import annotations

from ..client import QbitClient
from ..models import Action, Change, TorrentInfo
from .base import TorrentField


class NameField(TorrentField):
    name = "name"
    description = "The torrent's display name in qBittorrent."
    multi = False
    actions = (Action.SET, Action.EDIT)

    def values(self, torrent: TorrentInfo) -> tuple[str, ...]:
        return (torrent.name,)

    def apply(self, client: QbitClient, change: Change) -> None:
        client.rename(change.torrent.hash, change.new)
