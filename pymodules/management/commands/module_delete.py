"""
python manage.py module_delete <ModuleName> [--yes]

Delete a module from disk.

Examples:
    python manage.py module_delete Blog
    python manage.py module_delete Blog --yes   # skip confirmation
"""
import shutil

from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Delete a pymodules module from disk."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Module name to delete.")
        parser.add_argument(
            "--yes", action="store_true",
            help="Skip the confirmation prompt.",
        )

    def handle(self, *args, **options):
        name = options["name"]
        yes  = options["yes"]

        registry = get_registry()
        try:
            module = registry.find(name)
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        if not yes:
            confirm = input(f"  Delete module '{name}' at {module.path}? [y/N] ")
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write("  Aborted.")
                return

        shutil.rmtree(module.path)
        registry.scan()
        self.stdout.write(self.style.SUCCESS(f"✓ Module '{name}' deleted."))
