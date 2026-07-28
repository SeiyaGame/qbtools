"""The category field: single-valued, set/edit."""

from __future__ import annotations

from ..client import QbitClient
from ..models import Action, Change, TorrentInfo
from .base import TorrentField


class CategoryField(TorrentField):
    name = "category"
    description = "The single category each torrent belongs to."
    multi = False
    actions = (Action.SET, Action.EDIT)
    lists_values = True

    def values(self, torrent: TorrentInfo) -> tuple[str, ...]:
        return (torrent.category,)

    def known_values(self, client: QbitClient) -> list[str]:
        return client.categories()

    def apply(self, client: QbitClient, change: Change) -> None:
        # SET and EDIT both land on the same call - the new value is already computed.
        client.set_category(change.torrent.hash, change.new)
