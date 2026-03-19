"""
python manage.py module_make_api_urls <ModuleName> [--model ModelName] [--api-prefix PREFIX]

Generate or update api/urls.py with a DRF DefaultRouter for a module's ViewSets.

Examples:
    python manage.py module_make_api_urls Blog
    python manage.py module_make_api_urls Blog --model Post
    python manage.py module_make_api_urls Blog --api-prefix posts
"""
from __future__ import annotations

from pathlib import Path

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
                "URL prefix used when mounted by api_url_patterns(). "
                "Defaults to module name lowercased."
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
            raise CommandError(
                f"api/urls.py already exists in module '{module.name}'. "
                "Use --force to overwrite."
            )

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
