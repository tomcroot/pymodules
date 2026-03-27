"""Typed runtime contracts for pymodules v2-compatible modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol


@dataclass(frozen=True)
class ModuleMeta:
    """Static module metadata used by the v2 runtime contract."""

    name: str
    key: str
    version: str
    description: str = ""
    dependencies: tuple[str, ...] = ()
    optional_dependencies: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    enabled_by_default: bool = True


class RegistryProtocol(Protocol):
    """Protocol for extension-point registration during module register()."""

    def add(self, extension_point: str, value: Any, *, module: str) -> None:
        ...

    def add_many(
        self,
        extension_point: str,
        values: Iterable[Any],
        *,
        module: str,
    ) -> None:
        ...


class BaseModule:
    """Base class for v2-style typed modules."""

    meta: ModuleMeta

    def register(self, registry: RegistryProtocol) -> None:
        """Declare extension contributions. Override in subclasses."""

    def boot(self, app: Any | None = None) -> None:
        """Initialize runtime behavior after global registration."""

    def shutdown(self, app: Any | None = None) -> None:
        """Cleanup hook called during registry shutdown."""

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True}
