"""The tags field: multi-valued, add/remove/edit (edit = remove old + add new)."""

from __future__ import annotations

from ..client import QbitClient
from ..models import Action, Change, TorrentInfo
from .base import TorrentField


class TagField(TorrentField):
    name = "tags"
    description = "Free-form tags on each torrent."
    multi = True
    actions = (Action.EDIT, Action.ADD, Action.REMOVE)
    lists_values = True

    def values(self, torrent: TorrentInfo) -> tuple[str, ...]:
        return torrent.tags

    def known_values(self, client: QbitClient) -> list[str]:
        return client.tags()

    def apply(self, client: QbitClient, change: Change) -> None:
        h = change.torrent.hash
        if change.action is Action.ADD:
            client.add_tags(h, change.new)
        elif change.action is Action.REMOVE:
            client.remove_tags(h, change.old)
        elif change.action is Action.EDIT:  # rename: drop the old, add the rewritten
            client.remove_tags(h, change.old)
            client.add_tags(h, change.new)
