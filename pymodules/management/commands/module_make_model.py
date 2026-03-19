"""
python manage.py module_make_model <ModuleName> <ModelName> [--abstract] [--proxy]

Create a lightweight Django model scaffold in a module without bloat.

Examples:
    python manage.py module_make_model Blog Post
    python manage.py module_make_model Auth User --abstract
    python manage.py module_make_model Shop Order --proxy

Each model is created as a separate file in models/{model_lower}.py (not monolithic),
then automatically exported via models/__init__.py.
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError  # type: ignore[import]

from pymodules.exceptions import ModuleNotFoundError
from pymodules.management._base import get_registry


class Command(BaseCommand):
    help = "Create a lightweight Django model scaffold in a module (non-bloated)."

    def add_arguments(self, parser):
        parser.add_argument("module_name", help="Module name where model will be created.")
        parser.add_argument("model_name", help="Name of the model class to create.")
        parser.add_argument("--abstract", action="store_true", help="Create an abstract base model.")
        parser.add_argument("--proxy", action="store_true", help="Create a proxy model (requires parent model).")

    def handle(self, *args, **options):
        registry = get_registry()

        try:
            module = registry.find(options["module_name"])
        except ModuleNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        model_name = options["model_name"]
        model_lower = model_name.lower()
        is_abstract = options["abstract"]
        is_proxy = options["proxy"]

        # Ensure models directory exists
        models_dir = module.path / "models"
        if not models_dir.exists():
            models_dir.mkdir(parents=True)

        # Create models/__init__.py if it doesn't exist
        init_path = models_dir / "__init__.py"
        if not init_path.exists():
            init_path.write_text('"""Models for the module."""\n')

        # Create model file
        model_file = models_dir / f"{model_lower}.py"
        if model_file.exists():
            raise CommandError(f"Model file already exists: {model_file}")

        model_code = self._generate_model(model_name, model_lower, is_abstract, is_proxy, module.name)
        model_file.write_text(model_code)

        # Update models/__init__.py to export the model
        self._update_models_init(init_path, model_name, model_lower)

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Model '{model_name}' created at {model_file.relative_to(module.path)}."
            )
        )
        self.stdout.write(
            f"  Exported in models/__init__.py.\n"
        )

    def _generate_model(
        self, model_name: str, model_lower: str, is_abstract: bool, is_proxy: bool, module_name: str
    ) -> str:
        """Generate model code scaffold."""
        
        if is_abstract:
            class_def = f"class {model_name}(models.Model):"
            meta = f"""\
    class Meta:
        abstract = True"""
        elif is_proxy:
            class_def = f"class {model_name}(models.Model):"
            meta = f"""\
    class Meta:
        proxy = True
        app_label = "{module_name.lower()}\""""
        else:
            class_def = f"class {model_name}(models.Model):"
            meta = f"""\
    class Meta:
        app_label = "{module_name.lower()}"
        verbose_name = "{model_name}"
        verbose_name_plural = "{model_name}s\""""

        return f'''\
"""Model for the {module_name} module — {model_name}."""
from django.db import models


{class_def}
    """Lightweight {model_name} model."""
    
    # TODO: Add your fields here
    # name = models.CharField(max_length=200)
    # description = models.TextField(blank=True, null=True)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    {meta}

    def __str__(self) -> str:
        return self.name  # Adjust to your model fields
'''

    def _update_models_init(self, init_path: Path, model_name: str, model_lower: str) -> None:
        """Update models/__init__.py to export the model."""
        content = init_path.read_text()
        
        # Check if already exported
        if f"from .{model_lower} import {model_name}" in content:
            return
        
        # Add import at the end of the file
        if content.strip():
            content = content.rstrip() + f"\nfrom .{model_lower} import {model_name}\n"
        else:
            content = f'"""Models for the module."""\nfrom .{model_lower} import {model_name}\n'
        
        init_path.write_text(content)
