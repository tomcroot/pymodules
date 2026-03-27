"""Compatibility helpers for bridging v1 providers into newer runtimes."""
from __future__ import annotations

import importlib
from typing import Any

from .module import Module


class LegacyProviderAdapter:
    """
    Adapter for v1 ServiceProvider instances.

    This preserves the v1 register()/boot() lifecycle while exposing a
    stable surface for future runtimes that may also call shutdown().
    """

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def register(self) -> None:
        self._provider.register()

    def boot(self) -> None:
        self._provider.boot()

    def shutdown(self) -> None:
        shutdown = getattr(self._provider, "shutdown", None)
        if callable(shutdown):
            shutdown()


def load_legacy_provider(
    provider_path: str,
    module: Module,
    *,
    app: Any = None,
) -> LegacyProviderAdapter:
    """Import and instantiate a v1 provider class, wrapped in an adapter."""
    try:
        mod_path, cls_name = provider_path.rsplit(".", 1)
        imported = importlib.import_module(mod_path)
        provider_cls = getattr(imported, cls_name)
        provider = provider_cls(module, app=app)
        return LegacyProviderAdapter(provider)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Failed to boot provider {provider_path!r} "
            f"for module {module.name!r}: {exc}"
        ) from exc
