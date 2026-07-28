"""Tracker operations: each turns the selection into a list of planned changes.

Any module dropped in this package is imported automatically, so a new operation
only has to exist to get its place in the registry (and in `qbt.py operations`).
"""

from ..registry import import_submodules
from .base import REGISTRY, TrackerOperation

# Import every module so each TrackerOperation subclass registers on definition.
import_submodules(__name__, __path__)


def operation_names() -> list[str]:
    """Every registered operation name, in registration order."""
    return TrackerOperation.names()


def operation_for(name: str) -> type[TrackerOperation]:
    """The operation class handling a name. Raises on an unknown one."""
    return TrackerOperation.by_name(name)


__all__ = ["REGISTRY", "TrackerOperation", "operation_for", "operation_names"]
