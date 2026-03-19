"""
ServiceProvider — base class for module boot/register logic.

Each module can define one or more service providers in module.json:

    {
        "providers": ["modules.Blog.providers.BlogServiceProvider"]
    }

Example provider::

    # modules/Blog/providers.py
    from pymodules import ServiceProvider

    class BlogServiceProvider(ServiceProvider):
        def register(self):
            # bind things into a container, register signals, etc.
            self.app.bind("blog.repository", BlogRepository)

        def boot(self):
            # run after all providers registered
            self.register_routes()
            self.register_config()

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .module import Module


class ServiceProvider:
    """
    Base class for a module service provider.

    Subclass this inside your module and reference it in module.json:

        {
            "providers": ["modules.YourModule.providers.YourServiceProvider"]
        }
    """

    def __init__(self, module: "Module", app: Any = None) -> None:
        self.module = module
        self.app = app  # optional DI container or app object

    def register(self) -> None:
        """
        Called during module boot.  Override to register bindings,
        event listeners, middleware, etc.
        """

    def boot(self) -> None:
        """
        Called after all modules have been registered.
        Override for setup that depends on other modules.
        """

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def merge_config(self, key: str, path: str) -> None:
        """
        Merge a config file into the application config under ``key``.
        No-op in the base class — frameworks override this.
        """

    def load_routes(self, path: str) -> None:
        """
        Load a routes file for the module.
        No-op in the base class — framework integrations override this.
        """

    def load_migrations(self, path: str | None = None) -> None:
        """
        Register migration directory.
        No-op in the base class — framework integrations override this.
        """

    def publishes(self, paths: dict[str, str], group: str | None = None) -> None:
        """
        Declare assets/files that should be published to the host app.
        Stores publish map in module manifest for the publish command.
        """
        existing = self.module.manifest.get("publishes", {})
        key = group or "default"
        existing.setdefault(key, {}).update(paths)
        manifest = dict(self.module.manifest)
        manifest["publishes"] = existing
        self.module.save_manifest(manifest)
