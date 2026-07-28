"""Common interface for the operations (replace / add / remove / set).

An operation is the *how*; a `TorrentField` is the *what* (see `fields/`). The same
operation drives any field: `replace` rewrites a value whether it's a tracker URL,
a tag or a category. Adding one = drop a module here with a `FieldOperation`
subclass; it self-registers and shows up in `qbt.py operations`.

An operation is a *pure planner*: given a field and one `TorrentInfo` it returns
the `Change`s it would make, and never touches the network. The engine
(`engine.py`) is the only thing that applies them - so dry-run and apply share the
exact same computation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..models import Action, Change, TorrentInfo
from ..registry import Registry

if TYPE_CHECKING:
    from ..fields import TorrentField


class FieldOperation(Registry, ABC):
    """One bulk edit, generic over the field it acts on."""

    _registry_label = "Operation"
    name: str = ""  # CLI verb / discovery key (e.g. "replace")
    description: str = ""  # one-line help
    #: The kind of change this operation emits; a field advertises which it accepts.
    action: Action

    @classmethod
    def _validate_registration(cls) -> None:
        super()._validate_registration()
        if not isinstance(getattr(cls, "action", None), Action):
            raise ValueError(f"Operation {cls.__name__} must set `action` to an Action member.")

    @abstractmethod
    def changes(self, field: TorrentField, torrent: TorrentInfo) -> list[Change]:
        """The changes this operation would make to one torrent's field (may be empty)."""


#: The registered operations, in definition order (`from .base import REGISTRY`).
REGISTRY: list[type[FieldOperation]] = FieldOperation.REGISTRY
