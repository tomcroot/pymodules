"""
python manage.py module_make_model_migration <ModuleName> <ModelName> [--auto-name] [--empty] [--dry-run]

Create a migration for a specific model within a module (useful when models are separated per file).

Examples:
    python manage.py module_make_model_migration Blog Post
    python manage.py module_make_model_migration Blog Post --auto-name
    python manage.py module_make_model_migration Blog Post --auto-name --dry-run

When --auto-name is used, the migration name is auto-generated as "add_{model_lower}".
Without it, Django's default auto-naming applies.
"""
from __future__ import annotations

from django.core.management import call_command  # type: ignore[import]
from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Create a migration for a specific model within a module."

    def add_arguments(self, parser):
        parser.add_argument("module_name", help="Module name where model resides.")
        parser.add_argument("model_name", help="Model class name to create migration for.")
        parser.add_argument(
            "--auto-name",
            action="store_true",
            help="Auto-name migration as 'add_{model_lower}' (e.g., 'add_post').",
        )
        parser.add_argument("--empty", action="store_true", help="Create an empty migration.")
        parser.add_argument("--dry-run", action="store_true", help="Just show what would be done.")

    def handle(self, *args, **options):
        registry = get_registry()

        try:
            module = registry.find(options["module_name"])
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        model_name = options["model_name"]
        model_lower = model_name.lower()

        # Verify model file exists in the module
        model_file = module.path / "models" / f"{model_lower}.py"
        if not model_file.exists():
            raise CommandError(
                f"Model file not found: models/{model_lower}.py in module '{module.name}'. "
                f"Use 'module_make_model {module.name} {model_name}' to create it first."
            )

        kwargs = {
            "dry_run": options["dry_run"],
        }

        # If --auto-name, set the migration name
        if options["auto_name"]:
            kwargs["name"] = f"add_{model_lower}"

        if options["empty"]:
            kwargs["empty"] = True

        call_command("makemigrations", module.name.lower(), **kwargs)
        
        if options["auto_name"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Migration for model '{model_name}' created with name 'add_{model_lower}'."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Migration for model '{model_name}' created successfully."
                )
            )
