"""
python manage.py module_publish [ModuleName] [--group GROUP] [--force]

Publish module assets / config files to the host application.

Examples:
    python manage.py module_publish Blog
    python manage.py module_publish Blog --group config
    python manage.py module_publish            # publish all enabled modules
    python manage.py module_publish --force    # overwrite existing files
"""
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Publish module assets/config to the host Django application."

    def add_arguments(self, parser):
        parser.add_argument(
            "name", nargs="?", default=None,
            help="Module name. Omit to publish all enabled modules.",
        )
        parser.add_argument(
            "--group", default="default",
            help="Publish group (defined in module.json). Default: 'default'.",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Overwrite existing files.",
        )

    def handle(self, *args, **options):
        name  = options["name"]
        group = options["group"]
        force = options["force"]

        registry = get_registry()

        if name:
            try:
                targets = [registry.find(name)]
            except ModuleNotFoundError as exc:
                raise CommandError(str(exc)) from exc
        else:
            targets = registry.all_enabled()

        any_published = False
        for m in targets:
            publishes = m.manifest.get("publishes", {}).get(group, {})
            for src, dest in publishes.items():
                src_path  = m.path / src
                dest_path = Path(dest)
                if dest_path.exists() and not force:
                    self.stdout.write(f"  skip {dest}  (use --force to overwrite)")
                    continue
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
                self.stdout.write(self.style.SUCCESS(f"  ✓ {src} → {dest}"))
                any_published = True

        if not any_published:
            self.stdout.write("  Nothing to publish.")
