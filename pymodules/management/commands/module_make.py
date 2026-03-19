"""
python manage.py module_make <ModuleName> [--preset PRESET] [--force]

Creates a new module scaffold. Equivalent to `pymodules make`.

Examples:
    python manage.py module_make Blog
    python manage.py module_make Blog --preset django
    python manage.py module_make Auth --force
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.generator import ModuleGenerator, PRESETS
from pymodules.exceptions import ModuleAlreadyExistsError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Create a new pymodules module scaffold."

    def add_arguments(self, parser):
        parser.add_argument(
            "name",
            help="Module name in PascalCase (e.g. Blog, UserAuth, PaymentGateway).",
        )
        parser.add_argument(
            "--preset", "-p",
            choices=list(PRESETS),
            default=None,
            help=(
                "Scaffold preset. "
                "Choices: %(choices)s. "
                "Defaults to pymodules.toml default_preset, then 'django' "
                "(since you're using manage.py)."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite the module if it already exists.",
        )

    def handle(self, *args, **options):
        name    = options["name"]
        force   = options["force"]
        preset  = options["preset"]

        registry = get_registry()

        # When running via manage.py we know this is a Django project.
        # If the user didn't specify a preset, resolve via the same
        # priority chain as the standalone CLI but default to 'django'
        # instead of 'default', since manage.py implies Django.
        if preset is None:
            preset = self._resolve_preset(registry)

        generator = ModuleGenerator(registry, preset=preset, force=force)

        try:
            path = generator.generate(name)
        except ModuleAlreadyExistsError as exc:
            raise CommandError(str(exc) + "  Use --force to overwrite.") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"✓ Module '{name}' created at {path}"))
        self.stdout.write(f"  Preset : {preset}")
        self.stdout.write(f"  Folder : {registry.modules_root.name}/")
        self._print_tree(path)

    def _resolve_preset(self, registry) -> str:
        """
        Resolution order (manage.py context):
          1. pymodules.toml default_preset
          2. 'django'  ← manage.py = Django project, safe assumption
        """
        try:
            import tomllib
            from pathlib import Path
            cfg_file = Path.cwd() / "pymodules.toml"
            if cfg_file.exists():
                with cfg_file.open("rb") as f:
                    cfg = tomllib.load(f).get("pymodules", {})
                    if "default_preset" in cfg:
                        return cfg["default_preset"]
        except Exception:
            pass
        return "django"

    def _print_tree(self, base, indent="  "):
        for item in sorted(base.rglob("*")):
            if item.name == ".gitkeep":
                continue
            rel   = item.relative_to(base)
            depth = len(rel.parts)
            pad   = indent + "  " * (depth - 1)
            self.stdout.write(f"{pad}{'  ' if item.is_dir() else '  '}{item.name}")
