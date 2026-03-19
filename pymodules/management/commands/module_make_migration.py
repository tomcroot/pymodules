"""
python manage.py module_make_migration <ModuleName> [--name MIGRATION_NAME] [--empty] [--merge] [--dry-run] [--noinput]

Create migrations for a specific module (Django app label = module name lowercased).

Examples:
    python manage.py module_make_migration Blog
    python manage.py module_make_migration Blog --name add_status_field
    python manage.py module_make_migration Blog --empty --name seed_flags
"""
from __future__ import annotations

from django.core.management import call_command  # type: ignore[import]
from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Run Django makemigrations for a specific module."

    def add_arguments(self, parser):
        parser.add_argument("module_name", help="Module name to generate migrations for.")
        parser.add_argument("--name", dest="migration_name", default=None, help="Use this migration name.")
        parser.add_argument("--empty", action="store_true", help="Create an empty migration.")
        parser.add_argument("--merge", action="store_true", help="Enable fixing of migration conflicts.")
        parser.add_argument("--dry-run", action="store_true", help="Just show what migrations would be made.")
        parser.add_argument("--noinput", action="store_true", help="Do not prompt for input.")

    def handle(self, *args, **options):
        registry = get_registry()

        try:
            module = registry.find(options["module_name"])
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        kwargs = {
            "name": options["migration_name"],
            "empty": options["empty"],
            "merge": options["merge"],
            "dry_run": options["dry_run"],
            "interactive": not options["noinput"],
        }

        # Avoid overriding the positional module name by passing None.
        if kwargs["name"] is None:
            del kwargs["name"]

        call_command("makemigrations", module.name.lower(), **kwargs)
        self.stdout.write(self.style.SUCCESS(f"✓ Migration generation processed for module '{module.name}'."))
