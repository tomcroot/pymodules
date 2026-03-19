"""
ModuleRegistry — discovers, loads, enables/disables, and boots all modules.
This is the central object that applications interact with.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from .module import Module
from .exceptions import ModuleDependencyError, ModuleNotFoundError


class ModuleRegistry:
    """
    Central registry that manages all modules within a project.

    Usage (framework-agnostic)::

        from pymodules import ModuleRegistry

        registry = ModuleRegistry(modules_path="modules")
        registry.boot()

        blog = registry.find("Blog")
        blog.enable()

    Django integration::

        # settings.py
        from pymodules.integrations.django import DjangoModuleRegistry
        registry = DjangoModuleRegistry(modules_path="modules")
        INSTALLED_APPS += registry.installed_apps()
        MODULE_REGISTRY = registry

    """

    def __init__(
        self,
        modules_path: str | Path = "modules",
        *,
        scan_on_init: bool = True,
    ) -> None:
        self.modules_root = Path(modules_path).resolve()
        self._modules: dict[str, Module] = {}
        self._booted = False
        self._boot_hooks: list[Callable[[Module], None]] = []

        if scan_on_init:
            self.scan()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def scan(self) -> None:
        """Scan the modules directory and register all found modules."""
        self._modules.clear()
        if not self.modules_root.exists():
            return

        for entry in sorted(self.modules_root.iterdir()):
            if entry.is_dir() and not entry.name.startswith((".", "_")):
                module = Module(name=entry.name, path=entry, registry=self)
                self._modules[entry.name] = module

    # ------------------------------------------------------------------
    # Boot
    # ------------------------------------------------------------------

    def boot(self) -> None:
        """
        Boot all enabled modules.
        - Adds module root to sys.path if needed.
        - Imports and calls each module's service providers.
        - Invokes registered boot hooks.
        """
        if self._booted:
            return

        # Ensure the parent of modules_root is on sys.path so that
        # `import modules.Blog.models` works.
        parent = str(self.modules_root.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)

        boot_plan: list[tuple[Module, list[Any]]] = []

        # 1) Register every provider for every enabled module.
        for module in self.all_enabled_ordered():
            providers = self._instantiate_providers(module)
            for provider in providers:
                provider.register()
            boot_plan.append((module, providers))

        # 2) Boot providers after registration has completed globally.
        for _, providers in boot_plan:
            for provider in providers:
                provider.boot()

        # 3) Run module boot hooks.
        for module, _ in boot_plan:
            for hook in self._boot_hooks:
                hook(module)

        self._booted = True

    def _instantiate_providers(self, module: Module) -> list[Any]:
        providers: list[Any] = []
        for provider_path in module.providers:
            try:
                parts = provider_path.rsplit(".", 1)
                mod = importlib.import_module(parts[0])
                provider_cls = getattr(mod, parts[1])
                providers.append(provider_cls(module, app=self._provider_app()))
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"Failed to boot provider {provider_path!r} "
                    f"for module {module.name!r}: {exc}"
                ) from exc
        return providers

    def _provider_app(self) -> Any | None:
        """
        Return the application/container object passed to service providers.
        Framework-specific registries can override this.
        """
        return None

    def on_boot(self, fn: Callable[[Module], None]) -> Callable[[Module], None]:
        """Register a hook called for every enabled module during boot."""
        self._boot_hooks.append(fn)
        return fn

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def all(self) -> list[Module]:
        return list(self._modules.values())

    def all_enabled(self) -> list[Module]:
        return [m for m in self._modules.values() if m.is_enabled]

    def all_enabled_ordered(self) -> list[Module]:
        """
        Return enabled modules in dependency order.

        Modules can declare dependencies in module.json via:
            "requires": ["Core", "Accounting"]
        """
        enabled = {m.name: m for m in self.all_enabled()}
        if not enabled:
            return []

        in_degree: dict[str, int] = {name: 0 for name in enabled}
        graph: dict[str, list[str]] = {name: [] for name in enabled}

        for module in enabled.values():
            for dep_name in module.requires:
                if dep_name == module.name:
                    raise ModuleDependencyError(
                        f"Module {module.name!r} cannot depend on itself."
                    )

                dep_module = self._modules.get(dep_name)
                if dep_module is None:
                    raise ModuleDependencyError(
                        f"Module {module.name!r} requires missing module {dep_name!r}."
                    )
                if not dep_module.is_enabled:
                    raise ModuleDependencyError(
                        f"Module {module.name!r} requires disabled module {dep_name!r}."
                    )

                graph[dep_name].append(module.name)
                in_degree[module.name] += 1

        queue = sorted([name for name, degree in in_degree.items() if degree == 0])
        ordered_names: list[str] = []

        while queue:
            name = queue.pop(0)
            ordered_names.append(name)

            for dependent in sorted(graph[name]):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
            queue.sort()

        if len(ordered_names) != len(enabled):
            unresolved = sorted(name for name, degree in in_degree.items() if degree > 0)
            raise ModuleDependencyError(
                "Circular module dependency detected among: "
                + ", ".join(unresolved)
            )

        return [enabled[name] for name in ordered_names]

    def all_disabled(self) -> list[Module]:
        return [m for m in self._modules.values() if not m.is_enabled]

    def find(self, name: str) -> Module:
        """Return a module by name, raises ModuleNotFoundError if missing."""
        try:
            return self._modules[name]
        except KeyError:
            raise ModuleNotFoundError(name)

    def find_or_fail(self, name: str) -> Module:
        """Alias for find() — mirrors the Laravel naming."""
        return self.find(name)

    def exists(self, name: str) -> bool:
        return name in self._modules

    def count(self) -> int:
        return len(self._modules)

    def __iter__(self) -> Iterator[Module]:
        return iter(self._modules.values())

    def __contains__(self, name: str) -> bool:
        return self.exists(name)

    # ------------------------------------------------------------------
    # Enable / Disable
    # ------------------------------------------------------------------

    def enable(self, name: str) -> None:
        self.find(name).enable()

    def disable(self, name: str) -> None:
        self.find(name).disable()

    # ------------------------------------------------------------------
    # Module path helpers
    # ------------------------------------------------------------------

    def module_path(self, name: str, *parts: str) -> Path:
        """Return path within a module. Raises ModuleNotFoundError."""
        base = self.find(name).path
        return base / Path(*parts) if parts else base

    def assets_path(self, name: str) -> Path:
        return self.module_path(name, "assets")

    def config_path(self, name: str) -> Path:
        return self.module_path(name, "config", "config.py")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_module_object(self, name: str, path: Path) -> Module:
        module = Module(name=name, path=path, registry=self)
        self._modules[name] = module
        return module
