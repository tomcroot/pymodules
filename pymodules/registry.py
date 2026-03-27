"""
ModuleRegistry — discovers, loads, enables/disables, and boots all modules.
This is the central object that applications interact with.
"""
from __future__ import annotations

import importlib
from importlib import metadata
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Literal

from .compatibility import load_legacy_provider
from .contracts import BaseModule
from .extensions import ExtensionRegistry
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

    v2-compatible discovery controls::

        registry = ModuleRegistry(
            modules_path="modules",
            include_entry_points=True,
            discovery_order=("filesystem", "entry_points"),
            duplicate_policy="error",
        )

    """

    def __init__(
        self,
        modules_path: str | Path = "modules",
        *,
        scan_on_init: bool = True,
        include_entry_points: bool = False,
        entry_point_group: str = "pymodules.modules",
        discovery_order: tuple[str, ...] | None = None,
        duplicate_policy: Literal["error", "prefer-first", "prefer-last"] = "error",
    ) -> None:
        self.modules_root = Path(modules_path).resolve()
        self._modules: dict[str, Module] = {}
        self._typed_modules: dict[str, BaseModule] = {}
        self._extensions = ExtensionRegistry()
        self._boot_plan: list[tuple[Module, list[Any]]] = []
        self._registered = False
        self._booted = False
        self._boot_hooks: list[Callable[[Module], None]] = []
        self._include_entry_points = include_entry_points
        self._entry_point_group = entry_point_group
        if discovery_order is None:
            self._discovery_order = ("filesystem", "entry_points")
        else:
            self._discovery_order = discovery_order
        self._duplicate_policy = duplicate_policy

        unknown = set(self._discovery_order) - {"filesystem", "entry_points"}
        if unknown:
            raise ValueError(
                f"Unsupported discovery sources in discovery_order: {sorted(unknown)!r}"
            )
        if self._duplicate_policy not in {"error", "prefer-first", "prefer-last"}:
            raise ValueError(
                "duplicate_policy must be one of: 'error', 'prefer-first', 'prefer-last'"
            )

        if scan_on_init:
            self.scan()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def scan(self) -> None:
        """Scan all configured discovery sources and register found modules."""
        self._modules.clear()
        self._typed_modules = {}
        self._extensions = ExtensionRegistry()
        self._boot_plan = []
        self._registered = False
        self._booted = False
        for source in self._discovery_order:
            if source == "filesystem":
                self._scan_filesystem_modules()
            elif source == "entry_points" and self._include_entry_points:
                self.scan_entry_points()

    def _scan_filesystem_modules(self) -> None:
        """Discover modules from the local modules directory."""
        if not self.modules_root.exists():
            return
        for entry in sorted(self.modules_root.iterdir()):
            if entry.is_dir() and not entry.name.startswith((".", "_")):
                module = Module(name=entry.name, path=entry, registry=self)
                self._register_discovered_module(module, source="filesystem")

    def scan_entry_points(self) -> None:
        """Discover typed modules exposed through Python entry points.

        Entry-point modules are represented as in-memory Module instances with
        manifest defaults and a required `module_class` value.
        """
        for entry_point in self._iter_module_entry_points():
            module_name = entry_point.name
            module = Module(
                name=module_name,
                path=self.modules_root / module_name,
                registry=self,
            )
            module._manifest = {
                "name": module_name,
                "enabled": True,
                "module_class": entry_point.value,
                "providers": [],
                "requires": [],
            }
            self._register_discovered_module(module, source="entry_points")

    def _register_discovered_module(self, module: Module, *, source: str) -> None:
        """Register one discovered module using the configured duplicate policy."""
        existing = self._modules.get(module.name)
        if existing is None:
            self._modules[module.name] = module
            return

        if self._duplicate_policy == "error":
            raise RuntimeError(
                f"Duplicate module key {module.name!r} found while scanning {source!r}."
            )
        if self._duplicate_policy == "prefer-first":
            return

        self._modules[module.name] = module

    def _iter_module_entry_points(self) -> list[Any]:
        """Return entry points configured for pymodules module discovery."""
        points = metadata.entry_points()
        if hasattr(points, "select"):
            return list(points.select(group=self._entry_point_group))
        return list(points.get(self._entry_point_group, []))

    # ------------------------------------------------------------------
    # Boot
    # ------------------------------------------------------------------

    def discover(self) -> None:
        """v2 lifecycle alias for scan()."""
        self.scan()

    def resolve(self) -> list[str]:
        """Validate dependency ordering and return resolved module names."""
        return [module.name for module in self.all_enabled_ordered()]

    def instantiate(self) -> None:
        """Instantiate all configured typed modules for enabled modules."""
        loaded: dict[str, BaseModule] = {}
        for module in self.all_enabled_ordered():
            if not module.module_class:
                continue
            loaded[module.name] = self._instantiate_typed_module(module)
        self._typed_modules = loaded

    def register_all(self) -> None:
        """Register providers for all enabled modules without booting them."""
        if self._registered:
            return

        parent = str(self.modules_root.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)

        boot_plan: list[tuple[Module, list[Any]]] = []
        for module in self.all_enabled_ordered():
            providers = self._instantiate_providers(module)
            for provider in providers:
                provider.register()
            boot_plan.append((module, providers))

        if not self._typed_modules:
            self.instantiate()
        for module in self.all_enabled_ordered():
            typed = self._typed_modules.get(module.name)
            if typed is not None:
                typed.register(self)

        self._boot_plan = boot_plan
        self._registered = True

    def boot_all(self, app: Any | None = None) -> None:  # noqa: ARG002
        """Boot registered providers and execute module boot hooks."""
        if self._booted:
            return

        if not self._registered:
            self.register_all()

        for module in self.all_enabled_ordered():
            typed = self._typed_modules.get(module.name)
            if typed is not None:
                typed.boot(app=app)

        for _, providers in self._boot_plan:
            for provider in providers:
                provider.boot()

        for module, _ in self._boot_plan:
            for hook in self._boot_hooks:
                hook(module)

        self._booted = True

    def shutdown_all(self, app: Any | None = None) -> None:  # noqa: ARG002
        """Shutdown providers in reverse dependency order when supported."""
        if not self._registered:
            return

        for module in reversed(self.all_enabled_ordered()):
            typed = self._typed_modules.get(module.name)
            if typed is not None:
                typed.shutdown(app=app)

        for _, providers in reversed(self._boot_plan):
            for provider in reversed(providers):
                shutdown = getattr(provider, "shutdown", None)
                if callable(shutdown):
                    shutdown()

        self._typed_modules = {}
        self._boot_plan = []
        self._registered = False
        self._booted = False

    def boot(self) -> None:
        """
        Boot all enabled modules.
        - Adds module root to sys.path if needed.
        - Imports and calls each module's service providers.
        - Invokes registered boot hooks.
        """
        self.register_all()
        self.boot_all()

    def _instantiate_providers(self, module: Module) -> list[Any]:
        providers: list[Any] = []
        for provider_path in module.providers:
            providers.append(
                load_legacy_provider(provider_path, module, app=self._provider_app())
            )
        return providers

    def _instantiate_typed_module(self, module: Module) -> BaseModule:
        module_class = module.module_class
        if not module_class:
            raise RuntimeError(
                f"Module {module.name!r} does not declare a module_class for typed loading."
            )
        try:
            # Support both entry-point style (`module:attr`) and dotted paths.
            if ":" in module_class:
                mod_path, _, cls_name = module_class.partition(":")
            else:
                mod_path, cls_name = module_class.rsplit(".", 1)
            imported = importlib.import_module(mod_path)
            cls = getattr(imported, cls_name)
            instance = cls()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Failed to instantiate typed module {module_class!r} "
                f"for module {module.name!r}: {exc}"
            ) from exc

        if not isinstance(instance, BaseModule):
            raise RuntimeError(
                f"Typed module {module_class!r} for module {module.name!r} "
                "must inherit from BaseModule."
            )
        return instance

    def _provider_app(self) -> Any | None:
        """
        Return the application/container object passed to service providers.
        Framework-specific registries can override this.
        """
        return None

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------

    def add(self, point: str, value: Any, *, module: str) -> None:
        """Add a single extension value contributed by a module."""
        self._extensions.add(point, value, module=module)

    def add_many(self, point: str, values: Iterable[Any], *, module: str) -> None:
        """Add multiple extension values contributed by a module."""
        self._extensions.add_many(point, values, module=module)

    def extensions(self, point: str) -> list[Any]:
        """Get all registered values for one extension point."""
        return self._extensions.get(point)

    def extension_map(self, point: str) -> dict[str, list[Any]]:
        """Get extension values grouped by module for one point."""
        return self._extensions.map(point)

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
