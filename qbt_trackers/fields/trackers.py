"""The tracker-URL field: multi-valued, add/remove/edit."""

from __future__ import annotations

from ..client import QbitClient
from ..models import Action, Change, TorrentInfo
from .base import TorrentField


class TrackerField(TorrentField):
    name = "trackers"
    description = "Announce URLs of each torrent."
    multi = True
    actions = (Action.EDIT, Action.ADD, Action.REMOVE)

    def values(self, torrent: TorrentInfo) -> tuple[str, ...]:
        return tuple(t.url for t in torrent.real_trackers)

    def apply(self, client: QbitClient, change: Change) -> None:
        h = change.torrent.hash
        if change.action is Action.EDIT:
            client.edit_tracker(h, change.old, change.new)
        elif change.action is Action.ADD:
            client.add_tracker(h, change.new)
        elif change.action is Action.REMOVE:
            client.remove_tracker(h, change.old)
