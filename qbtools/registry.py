"""Auto-registering plugin base.

A concrete subclass validates and appends itself to its family's `REGISTRY` the
instant its `class` statement runs, so a new plugin only needs its module to be
imported (see `operations/__init__.py`). A direct subclass of `Registry` *roots* a
family with its own fresh `REGISTRY`; abstract intermediates are skipped.

Lifted from the sibling `downloader` project - the two share this one mechanism.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Iterable
from typing import ClassVar, Self


def import_submodules(package: str, path: Iterable[str]) -> None:
    """Import every module in a package so its plugins self-register on definition."""
    for module in pkgutil.iter_modules(path):
        importlib.import_module(f"{package}.{module.name}")


class Registry:
    """Mixin that turns a class hierarchy into a self-populating plugin registry."""

    #: Human label used in registration error messages ("Operation", ...).
    _registry_label: ClassVar[str] = "Plugin"
    #: Attribute a family is keyed by; must be non-empty and unique across members.
    _registry_key: ClassVar[str] = "name"
    #: Every registered member of the family - one fresh list per root class.
    REGISTRY: ClassVar[list]
    #: The plugin identifier; the default registry key.
    name: str = ""

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if Registry in cls.__bases__:
            cls.REGISTRY = []  # a direct subclass roots a new family
            return
        if inspect.isabstract(cls):
            return  # abstract intermediate: not a concrete plugin
        cls._validate_registration()
        cls.REGISTRY.append(cls)

    @classmethod
    def _validate_registration(cls) -> None:
        """Reject a malformed plugin (empty or duplicate key) before it registers."""
        if not cls.name:
            raise ValueError(f"{cls._registry_label} {cls.__name__} must define a non-empty `name`.")
        key = getattr(cls, cls._registry_key)
        if clash := next((c for c in cls.REGISTRY if getattr(c, cls._registry_key) == key), None):
            raise ValueError(f"{cls._registry_label} '{key}' is already registered by {clash.__name__}.")

    @classmethod
    def names(cls) -> list[str]:
        """Every registered plugin's `name`, in definition order."""
        return [c.name for c in cls.REGISTRY]

    @classmethod
    def by_name(cls, name: str) -> type[Self]:
        """The registered class with this `name`; raises on an unknown one."""
        for c in cls.REGISTRY:
            if c.name == name:
                return c
        raise ValueError(f"Unknown {cls._registry_label.lower()} '{name}'; expected one of {', '.join(cls.names())}.")
