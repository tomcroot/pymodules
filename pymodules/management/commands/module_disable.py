"""
python manage.py module_disable <ModuleName>

Disable a module (sets "enabled": false in its module.json).

Example:
    python manage.py module_disable Blog
"""
from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Disable a pymodules module."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Module name to disable.")

    def handle(self, *args, **options):
        name = options["name"]
        try:
            get_registry().disable(name)
            self.stdout.write(self.style.WARNING(f"✓ Module '{name}' disabled."))
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc
