"""
python manage.py module_show <ModuleName>

Show detailed info for a single module.

Example:
    python manage.py module_show Blog
"""
from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Show details for a single pymodules module."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Module name.")

    def handle(self, *args, **options):
        name = options["name"]
        try:
            m = get_registry().find(name)
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("")
        self.stdout.write(f"  Name        : {m.name}")
        self.stdout.write(f"  Status      : {'enabled' if m.is_enabled else 'disabled'}")
        self.stdout.write(f"  Version     : {m.version}")
        self.stdout.write(f"  Description : {m.description}")
        self.stdout.write(f"  Author      : {m.author}")
        self.stdout.write(f"  Path        : {m.path}")
        self.stdout.write(f"  Import path : {m.import_path}")
        if m.providers:
            self.stdout.write(f"  Providers   : {', '.join(m.providers)}")
        self.stdout.write("")
