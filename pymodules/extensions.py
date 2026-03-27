"""Extension registry for collecting module contributions by extension point."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


class ExtensionRegistry:
    """Stores extension values grouped by extension point and module key."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, list[Any]]] = defaultdict(dict)

    def add(self, extension_point: str, value: Any, *, module: str) -> None:
        module_values = self._data[extension_point].setdefault(module, [])
        module_values.append(value)

    def add_many(
        self,
        extension_point: str,
        values: Iterable[Any],
        *,
        module: str,
    ) -> None:
        module_values = self._data[extension_point].setdefault(module, [])
        module_values.extend(values)

    def get(self, extension_point: str) -> list[Any]:
        module_map = self._data.get(extension_point, {})
        collected: list[Any] = []
        for values in module_map.values():
            collected.extend(values)
        return collected

    def get_by_module(self, extension_point: str, module: str) -> list[Any]:
        module_map = self._data.get(extension_point, {})
        return list(module_map.get(module, []))

    def map(self, extension_point: str) -> dict[str, list[Any]]:
        module_map = self._data.get(extension_point, {})
        return {module: list(values) for module, values in module_map.items()}
