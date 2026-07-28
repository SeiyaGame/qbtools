"""Editable torrent fields (trackers, tags, category, save path, name).

A field is the *what* an operation acts on; the operation is the *how*. Each field
knows three things and nothing else:

* `values(torrent)`  - its current value(s) on a torrent (one for a single-valued
  field like category, many for a multi-valued one like tags);
* which `actions` make sense on it (multi-valued -> add/remove; single -> set);
* `apply(client, change)` - how to push one change back to qBittorrent.

Adding a field = drop a module in this package with a `TorrentField` subclass; it
self-registers, becomes the `qbt.py <field>` command group (exposing exactly the
operations it declares) and shows up in `qbt.py fields`, with nothing to edit in the
operations or the CLI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..client import QbitClient
from ..models import Action, Change, TorrentInfo
from ..registry import Registry


class TorrentField(Registry, ABC):
    """One editable property of a torrent."""

    _registry_label = "Field"
    name: str = ""  # command-group name / discovery key (e.g. "trackers")
    description: str = ""  # one-line help
    #: True for list-valued fields (trackers, tags): add/remove apply. False for
    #: single-valued ones (category, name, save path): set applies.
    multi: bool = False
    #: The actions that make sense on this field; the CLI exposes only these as
    #: sub-commands, so an unsupported combination can't even be typed.
    actions: tuple[Action, ...] = ()
    #: True when qBittorrent exposes the set of existing values (tags, categories),
    #: which the CLI surfaces as a `<field> list` sub-command.
    lists_values: bool = False

    @classmethod
    def _validate_registration(cls) -> None:
        super()._validate_registration()
        if not cls.actions:
            raise ValueError(f"Field {cls.__name__} must declare at least one supported action.")

    def supports(self, action: Action) -> bool:
        return action in self.actions

    def known_values(self, client: QbitClient) -> list[str]:
        """The values qBittorrent already knows for this field (for `<field> list`).

        Empty unless the field sets `lists_values` and overrides this.
        """
        return []

    @abstractmethod
    def values(self, torrent: TorrentInfo) -> tuple[str, ...]:
        """The field's current value(s) on a torrent."""

    @abstractmethod
    def apply(self, client: QbitClient, change: Change) -> None:
        """Push one change of this field back to qBittorrent."""


#: The registered fields, in definition order (`from .base import REGISTRY`).
REGISTRY: list[type[TorrentField]] = TorrentField.REGISTRY
