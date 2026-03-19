"""
python manage.py module_enable <ModuleName>

Enable a module (sets "enabled": true in its module.json).

Example:
    python manage.py module_enable Blog
"""
from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Enable a pymodules module."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Module name to enable.")

    def handle(self, *args, **options):
        name = options["name"]
        try:
            get_registry().enable(name)
            self.stdout.write(self.style.SUCCESS(f"✓ Module '{name}' enabled."))
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc
