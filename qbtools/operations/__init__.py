"""Tracker operations: each turns the selection into a list of planned changes.

Any module dropped in this package is imported automatically, so a new operation
only has to exist to get its place in the registry (and in `qbt.py operations`).
"""

from ..registry import import_submodules
from .base import REGISTRY, FieldOperation

# Import every module so each FieldOperation subclass registers on definition.
import_submodules(__name__, __path__)


def operation_names() -> list[str]:
    """Every registered operation name, in registration order."""
    return FieldOperation.names()


def operation_for(name: str) -> type[FieldOperation]:
    """The operation class handling a name. Raises on an unknown one."""
    return FieldOperation.by_name(name)


__all__ = ["REGISTRY", "FieldOperation", "operation_for", "operation_names"]
