"""
Shared base mixin for all pymodules Django management commands.

Provides registry resolution and styled output helpers so each command
stays focused on its own logic.
"""
from __future__ import annotations

from pathlib import Path
from django.conf import settings  # type: ignore[import]


def get_registry():
    """
    Resolve the DjangoModuleRegistry from Django settings.

    Looks for MODULE_REGISTRY in settings (the recommended approach).
    Falls back to constructing one from PYMODULES_PATH or 'modules'.
    """
    if hasattr(settings, "MODULE_REGISTRY"):
        return settings.MODULE_REGISTRY

    # Fallback: construct a registry on the fly
    from pymodules.integrations.django import DjangoModuleRegistry

    modules_path = getattr(settings, "PYMODULES_PATH", "modules")
    return DjangoModuleRegistry(modules_path=modules_path)
