"""
Django integration for pymodules.

Setup in settings.py::

    from pymodules.integrations.django import DjangoModuleRegistry

    MODULE_REGISTRY = DjangoModuleRegistry(modules_path=BASE_DIR / "modules")

    INSTALLED_APPS = [
        "pymodules",          # ← registers manage.py module_* commands
        *MODULE_REGISTRY.installed_apps(),
    ]

    MIGRATION_MODULES = MODULE_REGISTRY.migration_modules()

    locals().update(MODULE_REGISTRY.collect_settings())

Management commands available::

    python manage.py module_make <ModuleName>                                    # Create new module
    python manage.py module_make_model <ModuleName> <ModelName>                # Create lightweight model
    python manage.py module_make_model_migration <ModuleName> <ModelName>      # Create migration for specific model
    python manage.py module_make_migration <ModuleName>                        # Generate migrations for entire module
    python manage.py module_migrate [ModuleName]                               # Run migrations
    python manage.py module_list                                               # List all modules
    python manage.py module_enable <ModuleName>                                # Enable module
    python manage.py module_disable <ModuleName>                               # Disable module

urls.py::

    urlpatterns = [
        path("admin/", admin.site.urls),
        *settings.MODULE_REGISTRY.url_patterns(),
    ]

Available manage.py commands once "pymodules" is in INSTALLED_APPS:

    python manage.py module_make  <Name> [--preset PRESET] [--force]
    python manage.py module_list  [--enabled | --disabled]
    python manage.py module_enable  <Name>
    python manage.py module_disable <Name>
    python manage.py module_show    <Name>
    python manage.py module_delete  <Name> [--yes]
    python manage.py module_publish [Name] [--group GROUP] [--force]
    python manage.py module_migrate [Name] [--database DB] [--fake] [--fake-initial] [--plan]
    python manage.py module_make_migration <Name> [--name MIGRATION_NAME] [--empty] [--merge]
"""
from __future__ import annotations

import importlib
import importlib.util
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from ..exceptions import ModuleDependencyError
from ..registry import ModuleRegistry
from ..module import Module

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# AppConfig — makes pymodules a proper Django app so manage.py commands work
# ─────────────────────────────────────────────────────────────────────────────

class PyModulesConfig:
    """
    Minimal Django AppConfig shim.

    Add "pymodules" to INSTALLED_APPS and Django will discover the
    management/commands/ directory automatically, enabling all
    `python manage.py module_*` commands.
    """
    name            = "pymodules"
    label           = "pymodules"
    verbose_name    = "PyModules"
    default_auto_field = "django.db.models.BigAutoField"


# Register as the default app config so `"pymodules"` in INSTALLED_APPS
# resolves to this class automatically.
try:
    from django.apps import AppConfig  # type: ignore[import]

    class PyModulesAppConfig(AppConfig):
        name         = "pymodules"
        label        = "pymodules"
        verbose_name = "PyModules"
        default_auto_field = "django.db.models.BigAutoField"

        def ready(self):
            # Nothing to do on startup — management commands are
            # discovered by Django from management/commands/ automatically.
            pass

    default_app_config = "pymodules.integrations.django.PyModulesAppConfig"

except ImportError:
    pass  # Django not installed — no-op


# ─────────────────────────────────────────────────────────────────────────────
# DjangoModuleRegistry
# ─────────────────────────────────────────────────────────────────────────────

class DjangoModuleRegistry(ModuleRegistry):
    """
    ModuleRegistry subclass with Django-specific helpers.

    Provides:
      - installed_apps()      → list for INSTALLED_APPS
      - url_patterns()        → list for urlpatterns
      - migration_modules()   → dict for MIGRATION_MODULES
      - collect_settings()    → dict merged into Django settings
    """

    # ------------------------------------------------------------------
    # INSTALLED_APPS
    # ------------------------------------------------------------------

    def _enabled_modules_for_startup(self, context: str) -> list[Module]:
        """
        Return modules in dependency order when possible.

        During Django startup, dependency errors in module manifests are easier to
        diagnose if settings can still load. In that case, fall back to the plain
        enabled list and emit a warning.
        """
        try:
            return self.all_enabled_ordered()
        except ModuleDependencyError as exc:
            warnings.warn(
                f"pymodules could not resolve dependency order while building {context}: {exc}. "
                "Falling back to enabled module order so Django can finish startup.",
                RuntimeWarning,
                stacklevel=2,
            )
            return self.all_enabled()

    def installed_apps(self) -> list[str]:
        """
        Return dotted app paths for Django's INSTALLED_APPS.

        Detects AppConfig subclasses in each module's apps.py and
        returns the full dotted path. Falls back to the bare import path.
        """
        apps: list[str] = []
        for module in self._enabled_modules_for_startup("INSTALLED_APPS"):
            apps.append(self._resolve_app_config(module))
        return apps

    def _resolve_app_config(self, module: Module) -> str:
        if module.has_file("apps.py"):
            try:
                apps_mod = importlib.import_module(f"{module.import_path}.apps")
                from django.apps import AppConfig  # type: ignore[import]
                for attr in dir(apps_mod):
                    obj = getattr(apps_mod, attr)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, AppConfig)
                        and obj is not AppConfig
                    ):
                        return f"{module.import_path}.apps.{attr}"
            except Exception:
                pass
        return module.import_path

    # ------------------------------------------------------------------
    # URL patterns
    # ------------------------------------------------------------------

    def url_patterns(self) -> list:
        """
        Collect URL patterns from all enabled modules that define routes.py.

        Each module's routes.py should define:
            prefix = "blog"         # optional, defaults to module name lowercased
            urlpatterns = [...]

        Returns a list ready to be spread into urlpatterns::

            urlpatterns = [
                path("admin/", admin.site.urls),
                *settings.MODULE_REGISTRY.url_patterns(),
            ]
        """
        from django.urls import include, path  # type: ignore[import]

        patterns = []
        for module in self._enabled_modules_for_startup("urlpatterns"):
            if module.has_file("routes.py"):
                mod = importlib.import_module(f"{module.import_path}.routes")
                if hasattr(mod, "urlpatterns"):
                    prefix = getattr(mod, "prefix", module.name.lower())
                    patterns.append(path(f"{prefix}/", include(mod)))
        return patterns

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------

    def migration_modules(self) -> dict[str, str]:
        """
        Return a dict for Django's MIGRATION_MODULES setting.

        Maps each module's app label to its database/migrations package
        so Django finds migrations inside the module instead of the root.

        Usage::
            MIGRATION_MODULES = MODULE_REGISTRY.migration_modules()
        """
        result: dict[str, str] = {}
        for module in self._enabled_modules_for_startup("MIGRATION_MODULES"):
            migrations_path = module.path / "database" / "migrations"
            if migrations_path.exists():
                app_label = module.name.lower()
                result[app_label] = f"{module.import_path}.database.migrations"
        return result

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def collect_settings(self) -> dict:
        """
        Merge UPPER_CASE variables from every enabled module's
        config/config.py into a single dict.

        Usage (at the bottom of settings.py)::
            locals().update(MODULE_REGISTRY.collect_settings())
        """
        merged: dict = {}
        for module in self._enabled_modules_for_startup("settings collection"):
            config_file = module.path / "config" / "config.py"
            if config_file.exists():
                spec = importlib.util.spec_from_file_location(
                    f"{module.import_path}.config.config", config_file
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore[union-attr]
                    for key, val in vars(mod).items():
                        if key.isupper():
                            merged[key] = val
        return merged


# ─────────────────────────────────────────────────────────────────────────────
# Convenience helper
# ─────────────────────────────────────────────────────────────────────────────

def collect_urlpatterns(registry: ModuleRegistry) -> list:
    """Collect URL patterns from a DjangoModuleRegistry."""
    if isinstance(registry, DjangoModuleRegistry):
        return registry.url_patterns()
    raise TypeError("registry must be a DjangoModuleRegistry instance")
