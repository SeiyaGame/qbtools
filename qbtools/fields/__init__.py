"""Editable torrent fields: each exposes its current value(s) and how to write them.

Any module dropped in this package is imported automatically, so a new field only
has to exist to become a `--field` choice and show up in `qbt.py fields`.
"""

from ..registry import import_submodules
from .base import REGISTRY, TorrentField

# Import every module so each TorrentField subclass registers on definition.
import_submodules(__name__, __path__)


def field_names() -> list[str]:
    """Every registered field name, in registration order."""
    return TorrentField.names()


def field_for(name: str) -> TorrentField:
    """An instance of the field handling a name. Raises on an unknown one."""
    return TorrentField.by_name(name)()


__all__ = ["REGISTRY", "TorrentField", "field_for", "field_names"]
