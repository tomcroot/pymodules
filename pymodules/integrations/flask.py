"""
Flask integration for pymodules.

Usage::

    from flask import Flask
    from pymodules.integrations.flask import FlaskModuleRegistry

    app = Flask(__name__)
    registry = FlaskModuleRegistry(modules_path="modules", app=app)
    registry.boot()

Each module can expose a Blueprint in ``routes.py``::

    # modules/Blog/routes.py
    from flask import Blueprint

    blueprint = Blueprint("blog", __name__, url_prefix="/blog")

    @blueprint.route("/")
    def index():
        return "Blog index"
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from ..registry import ModuleRegistry

if TYPE_CHECKING:
    pass


class FlaskModuleRegistry(ModuleRegistry):
    """
    ModuleRegistry subclass with Flask-specific helpers.
    """

    def __init__(self, modules_path="modules", *, app: Any = None, **kwargs) -> None:
        self._flask_app = app
        super().__init__(modules_path, **kwargs)

    def init_app(self, app: Any) -> None:
        """Support Flask application factory pattern."""
        self._flask_app = app
        self.boot()

    def boot(self) -> None:
        super().boot()
        if self._flask_app is not None:
            self._register_blueprints(self._flask_app)

    def _provider_app(self) -> Any | None:
        return self._flask_app

    def _register_blueprints(self, app: Any) -> None:
        """Auto-register Blueprints from all enabled modules."""
        for module in self.all_enabled():
            if module.has_file("routes.py"):
                try:
                    mod = importlib.import_module(f"{module.import_path}.routes")
                    if hasattr(mod, "blueprint"):
                        app.register_blueprint(mod.blueprint)
                    elif hasattr(mod, "blueprints"):
                        for bp in mod.blueprints:
                            app.register_blueprint(bp)
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to register blueprint for module {module.name!r}: {exc}"
                    ) from exc
