"""
python manage.py module_make_serializer <ModuleName> <ModelName> [--list-fields FIELDS]

Generate a DRF ModelSerializer for an existing model inside a module.

Examples:
    python manage.py module_make_serializer Blog Post
    python manage.py module_make_serializer Blog Post --list-fields id,title,created_at
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Generate a DRF ModelSerializer for a module model."

    def add_arguments(self, parser):
        parser.add_argument("module_name", help="Module name.")
        parser.add_argument("model_name", help="Model class name to serialise.")
        parser.add_argument(
            "--list-fields",
            default=None,
            help=(
                "Comma-separated fields for the lightweight list serializer "
                "(default: id, name, created_at)."
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
        module_lower = module.name.lower()

        # Validate model file exists
        model_file = module.path / "models" / f"{model_lower}.py"
        if not model_file.exists():
            raise CommandError(
                f"Model file not found: models/{model_lower}.py in module "
                f"'{module.name}'. "
                f"Run `module_make_model {module.name} {model_name}` first."
            )

        # Determine list fields
        raw_list_fields = options["list_fields"]
        if raw_list_fields:
            list_fields = tuple(f.strip() for f in raw_list_fields.split(","))
        else:
            list_fields = ("id", "name", "created_at")

        list_fields_str = ", ".join(f'"{f}"' for f in list_fields)

        serializer_content = f'''\
"""DRF serializers for the {module.name} module — {model_name}."""
from rest_framework import serializers

from .models.{model_lower} import {model_name}


class {model_name}Serializer(serializers.ModelSerializer):
    """Full serializer — used for create / update endpoints."""

    class Meta:
        model = {model_name}
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class {model_name}ListSerializer(serializers.ModelSerializer):
    """Lightweight serializer — used for list endpoints."""

    class Meta:
        model = {model_name}
        fields = ({list_fields_str},)
'''

        serializer_file = module.path / "serializers.py"

        if serializer_file.exists():
            # Append to existing file rather than overwrite
            existing = serializer_file.read_text()
            if f"class {model_name}Serializer" in existing:
                raise CommandError(
                    f"Serializer for '{model_name}' already exists in "
                    f"{serializer_file}. Delete it manually to regenerate."
                )
            # Add import if not already present
            import_line = f"from .models.{model_lower} import {model_name}"
            if import_line not in existing:
                # Insert after the last existing import
                lines = existing.splitlines(keepends=True)
                insert_at = 0
                for i, line in enumerate(lines):
                    if line.startswith("from ") or line.startswith("import "):
                        insert_at = i + 1
                lines.insert(insert_at, import_line + "\n")
                existing = "".join(lines)

            serializer_file.write_text(
                existing.rstrip() + "\n\n\n" + serializer_content.lstrip("from")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Serializers for '{model_name}' appended to {serializer_file.name}."
                )
            )
        else:
            serializer_file.write_text(serializer_content)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {serializer_file.name} created for model '{model_name}'."
                )
            )

        self.stdout.write(f"  Classes: {model_name}Serializer, {model_name}ListSerializer")
