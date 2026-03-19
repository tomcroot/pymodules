"""
python manage.py module_list [--enabled] [--disabled]

Lists all modules and their status.

Examples:
    python manage.py module_list
    python manage.py module_list --enabled
    python manage.py module_list --disabled
"""
from django.core.management.base import BaseCommand  # type: ignore[import]

from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "List all pymodules modules."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--enabled",  action="store_true", help="Show only enabled modules.")
        group.add_argument("--disabled", action="store_true", help="Show only disabled modules.")

    def handle(self, *args, **options):
        registry = get_registry()
        modules  = registry.all()

        if options["enabled"]:
            modules = [m for m in modules if m.is_enabled]
        elif options["disabled"]:
            modules = [m for m in modules if not m.is_enabled]

        self.stdout.write(
            f"\nModules path: {registry.modules_root}/  ({len(modules)} found)\n"
        )

        if not modules:
            self.stdout.write("  No modules found. Run: python manage.py module_make <n>")
            return

        self.stdout.write(f"  {'Name':<25} {'Status':<10} {'Version':<10} Description")
        self.stdout.write("  " + "─" * 64)

        for m in modules:
            if m.is_enabled:
                status = self.style.SUCCESS("enabled")
            else:
                status = self.style.ERROR("disabled")
            self.stdout.write(f"  {m.name:<25} {status:<18} {m.version:<10} {m.description}")

        self.stdout.write("")
