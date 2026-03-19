"""
python manage.py module_migrate [ModuleName] [--database DB] [--fake] [--fake-initial] [--plan] [--noinput]

Run Django migrations for a specific module or for all apps.

Examples:
    python manage.py module_migrate
    python manage.py module_migrate Blog
    python manage.py module_migrate Blog --plan
"""
from __future__ import annotations

from django.core.management import call_command  # type: ignore[import]
from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Run Django migrate for a specific module (or all modules/apps)."

    def add_arguments(self, parser):
        parser.add_argument(
            "name",
            nargs="?",
            default=None,
            help="Module name. Omit to run full migrate.",
        )
        parser.add_argument("--database", default="default", help="Nominates a database to synchronize.")
        parser.add_argument("--fake", action="store_true", help="Mark migrations as run without actually running them.")
        parser.add_argument(
            "--fake-initial",
            action="store_true",
            help="Detect if tables already exist and fake-apply initial migrations if so.",
        )
        parser.add_argument("--plan", action="store_true", help="Show migration plan without applying migrations.")
        parser.add_argument("--noinput", action="store_true", help="Do not prompt for input.")

    def handle(self, *args, **options):
        registry = get_registry()
        name = options["name"]

        kwargs = {
            "database": options["database"],
            "fake": options["fake"],
            "fake_initial": options["fake_initial"],
            "plan": options["plan"],
            "interactive": not options["noinput"],
        }

        if name:
            try:
                module = registry.find(name)
            except ModuleNotFoundError as exc:
                raise CommandError(str(exc)) from exc

            call_command("migrate", module.name.lower(), **kwargs)
            self.stdout.write(self.style.SUCCESS(f"✓ Migrations processed for module '{module.name}'."))
            return

        call_command("migrate", **kwargs)
        self.stdout.write(self.style.SUCCESS("✓ Migrations processed for all apps."))
