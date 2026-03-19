"""
python manage.py module_make_viewset <ModuleName> <ModelName> [--read-only] [--actions LIST]

Generate a DRF ModelViewSet for an existing model inside a module.

Examples:
    python manage.py module_make_viewset Blog Post
    python manage.py module_make_viewset Blog Post --read-only
    python manage.py module_make_viewset Blog Post --actions list,retrieve,create
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry

_ALL_ACTIONS = {"list", "retrieve", "create", "update", "partial_update", "destroy"}


class Command(BaseCommand):
    help = "Generate a DRF ViewSet for a module model."

    def add_arguments(self, parser):
        parser.add_argument("module_name", help="Module name.")
        parser.add_argument("model_name", help="Model class name.")
        parser.add_argument(
            "--read-only",
            action="store_true",
            help="Generate a ReadOnlyModelViewSet instead of a full ModelViewSet.",
        )
        parser.add_argument(
            "--actions",
            default=None,
            help=(
                "Comma-separated subset of actions to allow "
                "(list, retrieve, create, update, partial_update, destroy). "
                "Ignored when --read-only is set."
            ),
        )

    def handle(self, *args, **options):
        registry = get_registry()

        try:
            module = registry.find(options["module_name"])
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        model_name = options["model_name"]
        model_lower = model_name.lower()
        read_only = options["read_only"]

        # Validate model exists
        model_file = module.path / "models" / f"{model_lower}.py"
        if not model_file.exists():
            raise CommandError(
                f"Model file not found: models/{model_lower}.py in module "
                f"'{module.name}'. "
                f"Run `module_make_model {module.name} {model_name}` first."
            )

        # Validate serializer exists
        serializer_file = module.path / "serializers.py"
        if not serializer_file.exists():
            raise CommandError(
                f"serializers.py not found in module '{module.name}'. "
                f"Run `module_make_serializer {module.name} {model_name}` first."
            )

        # Parse actions
        if read_only:
            base_class = "viewsets.ReadOnlyModelViewSet"
            http_method_names_line = ""
            actions_comment = "# Provides: list, retrieve"
        elif options["actions"]:
            requested = {a.strip() for a in options["actions"].split(",")}
            invalid = requested - _ALL_ACTIONS
            if invalid:
                raise CommandError(
                    f"Invalid actions: {', '.join(sorted(invalid))}. "
                    f"Choose from: {', '.join(sorted(_ALL_ACTIONS))}"
                )
            allowed = {
                "list": "GET",
                "retrieve": "GET",
                "create": "POST",
                "update": "PUT",
                "partial_update": "PATCH",
                "destroy": "DELETE",
            }
            http_methods = sorted({allowed[a] for a in requested})
            http_method_names_line = (
                f'    http_method_names = {[m.lower() for m in http_methods]}\n'
            )
            base_class = "viewsets.ModelViewSet"
            actions_comment = f"# Allowed actions: {', '.join(sorted(requested))}"
        else:
            base_class = "viewsets.ModelViewSet"
            http_method_names_line = ""
            actions_comment = "# Provides: list, retrieve, create, update, partial_update, destroy"

        viewset_content = f'''\
"""DRF ViewSet for the {module.name} module — {model_name}."""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models.{model_lower} import {model_name}
from .serializers import {model_name}Serializer, {model_name}ListSerializer


class {model_name}ViewSet({base_class}):
    """
    REST API endpoint for {model_name}.
    {actions_comment}
    """

    queryset = {model_name}.objects.all().order_by("-created_at")
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]
{http_method_names_line}
    def get_serializer_class(self):
        if self.action == "list":
            return {model_name}ListSerializer
        return {model_name}Serializer
'''

        viewset_file = module.path / "viewsets.py"

        if viewset_file.exists():
            existing = viewset_file.read_text()
            if f"class {model_name}ViewSet" in existing:
                raise CommandError(
                    f"ViewSet for '{model_name}' already exists in "
                    f"{viewset_file}. Delete it manually to regenerate."
                )
            viewset_file.write_text(existing.rstrip() + "\n\n\n" + viewset_content)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {model_name}ViewSet appended to {viewset_file.name}."
                )
            )
        else:
            viewset_file.write_text(viewset_content)
            self.stdout.write(
                self.style.SUCCESS(f"✓ {viewset_file.name} created for '{model_name}'.")
            )

        self.stdout.write(
            f"  Next: run `module_make_api_urls {module.name}` to wire it up."
        )
