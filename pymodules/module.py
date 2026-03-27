"""
Module class — represents a single module in the system.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any


class Module:
    """
    Represents a single self-contained module within a Python application.

    A module is a directory with a specific structure:
        <modules_root>/
            <ModuleName>/
                module.json        ← manifest
                __init__.py
                config.py          ← optional module config
                routes.py          ← optional routes (Flask/FastAPI/Django)
                models/
                views/ or controllers/
                services/
                tests/
    """

    def __init__(self, name: str, path: Path, registry: "ModuleRegistry") -> None:
        self.name = name
        self.path = path
        self._registry = registry
        self._manifest: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    @property
    def manifest_path(self) -> Path:
        return self.path / "module.json"

    @property
    def manifest(self) -> dict[str, Any]:
        if self._manifest is None:
            if self.manifest_path.exists():
                self._manifest = json.loads(self.manifest_path.read_text())
            else:
                self._manifest = {}
        return self._manifest

    def save_manifest(self, data: dict[str, Any]) -> None:
        self._manifest = data
        self.manifest_path.write_text(json.dumps(data, indent=4))

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self.manifest.get("enabled", True)

    def enable(self) -> None:
        manifest = dict(self.manifest)
        manifest["enabled"] = True
        self.save_manifest(manifest)

    def disable(self) -> None:
        manifest = dict(self.manifest)
        manifest["enabled"] = False
        self.save_manifest(manifest)

    # ------------------------------------------------------------------
    # Python import helpers
    # ------------------------------------------------------------------

    @property
    def import_path(self) -> str:
        """Dotted Python import path for this module's package."""
        # e.g. "modules.Blog"
        rel = self.path.relative_to(self._registry.modules_root.parent)
        return str(rel).replace("/", ".").replace("\\", ".")

    def import_submodule(self, subpath: str) -> Any:
        """
        Import a submodule within this module by dotted relative path.
        e.g. module.import_submodule("models.Post")
        """
        full = f"{self.import_path}.{subpath}"
        return importlib.import_module(full)

    def has_file(self, *parts: str) -> bool:
        return (self.path / Path(*parts)).exists()

    # ------------------------------------------------------------------
    # Metadata shortcuts
    # ------------------------------------------------------------------

    @property
    def version(self) -> str:
        return self.manifest.get("version", "0.1.0")

    @property
    def description(self) -> str:
        return self.manifest.get("description", "")

    @property
    def author(self) -> str:
        return self.manifest.get("author", "")

    @property
    def providers(self) -> list[str]:
        """List of dotted import paths for ModuleServiceProvider subclasses."""
        return self.manifest.get("providers", [])

    @property
    def module_class(self) -> str | None:
        """Optional dotted import path for a v2 BaseModule implementation."""
        value = self.manifest.get("module_class")
        return value if isinstance(value, str) and value else None

    @property
    def requires(self) -> list[str]:
        """List of module names this module depends on."""
        return self.manifest.get("requires", [])

    def __repr__(self) -> str:
        status = "enabled" if self.is_enabled else "disabled"
        return f"<Module {self.name!r} [{status}] at {self.path}>"
