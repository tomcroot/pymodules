"""
FastAPI integration for pymodules.

Usage::

    from fastapi import FastAPI
    from pymodules.integrations.fastapi import FastAPIModuleRegistry

    app = FastAPI()
    registry = FastAPIModuleRegistry(modules_path="modules", app=app)
    registry.boot()

Each module can expose an APIRouter in ``routes.py``::

    # modules/Blog/routes.py
    from fastapi import APIRouter

    router = APIRouter(prefix="/blog", tags=["blog"])

    @router.get("/")
    def index():
        return {"message": "Blog index"}
"""
from __future__ import annotations

import importlib
from typing import Any

from ..registry import ModuleRegistry


class FastAPIModuleRegistry(ModuleRegistry):
    """
    ModuleRegistry subclass with FastAPI-specific helpers.
    """

    def __init__(self, modules_path="modules", *, app: Any = None, **kwargs) -> None:
        self._fastapi_app = app
        super().__init__(modules_path, **kwargs)

    def init_app(self, app: Any) -> None:
        """Attach to a FastAPI app (supports app-factory pattern)."""
        self._fastapi_app = app
        self.boot()

    def boot(self) -> None:
        super().boot()
        if self._fastapi_app is not None:
            self._register_routers(self._fastapi_app)

    def _provider_app(self) -> Any | None:
        return self._fastapi_app

    def _register_routers(self, app: Any) -> None:
        """Auto-register APIRouters from all enabled modules."""
        for module in self.all_enabled():
            if module.has_file("routes.py"):
                try:
                    mod = importlib.import_module(f"{module.import_path}.routes")
                    if hasattr(mod, "router"):
                        app.include_router(mod.router)
                    elif hasattr(mod, "routers"):
                        for r in mod.routers:
                            app.include_router(r)
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to include router for module {module.name!r}: {exc}"
                    ) from exc
