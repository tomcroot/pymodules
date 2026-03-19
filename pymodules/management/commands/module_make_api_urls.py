"""
python manage.py module_make_api_urls <ModuleName> [--model ModelName] [--api-prefix PREFIX]

Generate or update api/urls.py with a DRF DefaultRouter for a module's ViewSets.

Examples:
    python manage.py module_make_api_urls Blog
    python manage.py module_make_api_urls Blog --model Post
    python manage.py module_make_api_urls Blog --api-prefix posts
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Generate api/urls.py wiring a DRF router for a module."

    def add_arguments(self, parser):
        parser.add_argument("module_name", help="Module name.")
        parser.add_argument(
            "--model",
            default=None,
            dest="model_name",
            help=(
                "Model/ViewSet name to register (default: inferred from module name). "
                "Example: --model Post registers PostViewSet."
            ),
        )
        parser.add_argument(
            "--api-prefix",
            default=None,
            help=(
                "For new files: URL mount prefix used by api_url_patterns(). "
                "For existing files: sub-route prefix for additional ViewSet registration."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing api/urls.py.",
        )

    def handle(self, *args, **options):
        registry = get_registry()

        try:
            module = registry.find(options["module_name"])
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        model_name = options["model_name"] or module.name
        api_prefix = options["api_prefix"] or module.name.lower()
        force = options["force"]

        # Validate viewset exists
        viewset_file = module.path / "viewsets.py"
        if not viewset_file.exists():
            raise CommandError(
                f"viewsets.py not found in module '{module.name}'. "
                f"Run `module_make_viewset {module.name} {model_name}` first."
            )
        if f"class {model_name}ViewSet" not in viewset_file.read_text():
            raise CommandError(
                f"{model_name}ViewSet not found in viewsets.py. "
                f"Run `module_make_viewset {module.name} {model_name}` first."
            )

        # Ensure api/ directory exists
        api_dir = module.path / "api"
        api_dir.mkdir(exist_ok=True)
        init_file = api_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")

        urls_file = api_dir / "urls.py"
        if urls_file.exists() and not force:
            route_prefix = options["api_prefix"] or model_name.lower()
            self._append_route(urls_file, model_name, route_prefix)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ api/urls.py updated for module '{module.name}' with route '{route_prefix}/'."
                )
            )
            self.stdout.write(
                f"  Registered {model_name}ViewSet at /api/<module>/{route_prefix}/\n"
            )
            return

        content = f'''\
"""API URL configuration for the {module.name} module.

Registered automatically by DjangoModuleRegistry.api_url_patterns()
at the prefix defined by `api_prefix` below.

The DRF DefaultRouter provides:
    GET    /api/{api_prefix}/          list
    POST   /api/{api_prefix}/          create
    GET    /api/{api_prefix}/{{id}}/     retrieve
    PUT    /api/{api_prefix}/{{id}}/     update
    PATCH  /api/{api_prefix}/{{id}}/     partial_update
    DELETE /api/{api_prefix}/{{id}}/     destroy
"""
from rest_framework.routers import DefaultRouter

from ..viewsets import {model_name}ViewSet

# Mounted at: /api/{api_prefix}/  (via DjangoModuleRegistry.api_url_patterns)
api_prefix = "{api_prefix}"

router = DefaultRouter()
router.register(r"", {model_name}ViewSet, basename="{api_prefix}")

urlpatterns = router.urls
'''

        urls_file.write_text(content)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ api/urls.py created for module '{module.name}'."
            )
        )
        self.stdout.write(
            f"\n  Add to your project urls.py:\n"
            f"    *settings.MODULE_REGISTRY.api_url_patterns()\n"
            f"\n  This mounts {module.name} API at: /api/{api_prefix}/\n"
        )

    def _append_route(self, urls_file, model_name: str, route_prefix: str) -> None:
        content = urls_file.read_text()
        viewset_name = f"{model_name}ViewSet"
        import_line_start = "from ..viewsets import "
        register_line = (
            f'router.register(r"{route_prefix}", {viewset_name}, basename="{route_prefix}")'
        )

        if register_line in content:
            raise CommandError(
                f"Route prefix '{route_prefix}' for {viewset_name} is already registered in api/urls.py."
            )

        # Update or insert import for the ViewSet.
        if import_line_start in content:
            pattern = re.compile(r"^from \.\.viewsets import (?P<items>.+)$", re.MULTILINE)
            match = pattern.search(content)
            if match:
                items = [item.strip() for item in match.group("items").split(",")]
                if viewset_name not in items:
                    items.append(viewset_name)
                    replacement = f"from ..viewsets import {', '.join(items)}"
                    content = pattern.sub(replacement, content, count=1)
        else:
            anchor = "from rest_framework.routers import DefaultRouter\n"
            import_line = f"from ..viewsets import {viewset_name}\n"
            if anchor in content:
                content = content.replace(anchor, anchor + "\n" + import_line, 1)
            else:
                content = import_line + "\n" + content

        # Insert registration before urlpatterns assignment when possible.
        marker = "urlpatterns = router.urls"
        if marker in content:
            content = content.replace(marker, register_line + "\n\n" + marker, 1)
        elif "router = DefaultRouter()" in content:
            content = content.replace("router = DefaultRouter()", "router = DefaultRouter()\n" + register_line, 1)
        else:
            raise CommandError("api/urls.py does not define a DefaultRouter; cannot append route safely.")

        urls_file.write_text(content)
