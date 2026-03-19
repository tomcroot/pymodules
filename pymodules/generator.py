"""
ModuleGenerator — creates a new module scaffold on disk.

Supports multiple scaffold presets:
  - "default"  : generic Python module (no framework assumptions)
  - "django"   : adds models.py, views.py, apps.py, admin.py, serializers.py
  - "fastapi"  : adds routes.py with APIRouter, schemas.py, services.py
  - "flask"    : adds routes.py with Blueprint, services.py
  - "plain"    : bare minimum — module.json + __init__.py only
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from .exceptions import ModuleAlreadyExistsError

if TYPE_CHECKING:
    from .registry import ModuleRegistry


# ─────────────────────────────────────────────────────────────────────────────
# Shared stubs
# ─────────────────────────────────────────────────────────────────────────────

_MANIFEST = """\
{{
    "name": "{module}",
    "version": "0.1.0",
    "description": "",
    "author": "",
    "enabled": true,
    "requires": [],
    "providers": [
        "{folder}.{module}.providers.{module}ServiceProvider"
    ]
}}
"""

_INIT = '"""The {module} module."""\n'

_PROVIDER = '''\
"""Service provider for the {module} module."""
from pymodules import ServiceProvider


class {module}ServiceProvider(ServiceProvider):
    def register(self) -> None:
        """Register {module} bindings / hooks here."""

    def boot(self) -> None:
        """Called after all modules have registered."""
'''

_CONFIG = '''\
"""Default configuration for the {module} module.

All UPPER_CASE variables are auto-merged into the host application settings
when using DjangoModuleRegistry.collect_settings().
"""

{module_upper}_SETTING_EXAMPLE = "change-me"
'''

_TEST = '''\
"""Tests for the {module} module."""
import pytest


class Test{module}:
    def test_placeholder(self) -> None:
        assert True
'''

# ─────────────────────────────────────────────────────────────────────────────
# Django stubs
# ─────────────────────────────────────────────────────────────────────────────

_DJANGO_APPS = '''\
"""Django AppConfig for the {module} module."""
from django.apps import AppConfig


class {module}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{folder}.{module}"
    label = "{module_lower}"
    verbose_name = "{module}"
'''

_DJANGO_MODELS = '''\
"""Models for the {module} module."""
from django.db import models


class {module}(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "{module_lower}"
        verbose_name = "{module}"
        verbose_name_plural = "{module}s"

    def __str__(self) -> str:
        return self.name
'''

_DJANGO_VIEWS = '''\
"""Views for the {module} module."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404

# from .models import {module}


def index(request: HttpRequest) -> HttpResponse:
    """List all {module} items."""
    # items = {module}.objects.all()
    return render(request, "{module_lower}/index.html", {{}})


def detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Show a single {module} item."""
    # item = get_object_or_404({module}, pk=pk)
    return render(request, "{module_lower}/detail.html", {{}})
'''

_DJANGO_ROUTES = '''\
"""URL configuration for the {module} module."""
from django.urls import path
from .views.{module_lower}_views import index, detail

# This prefix is used by DjangoModuleRegistry.url_patterns()
prefix = "{module_lower}"

app_name = "{module_lower}"

urlpatterns = [
    path("", index, name="index"),
    path("<int:pk>/", detail, name="detail"),
]
'''

_DJANGO_ADMIN = '''\
"""Django admin registration for the {module} module."""
from django.contrib import admin

# from .models import {module}

# @admin.register({module})
# class {module}Admin(admin.ModelAdmin):
#     list_display = ("name", "created_at")
#     search_fields = ("name",)
'''

_DJANGO_SERIALIZERS = '''\
"""DRF serializers for the {module} module (requires djangorestframework)."""
# from rest_framework import serializers
# from .models import {module}

# class {module}Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = {module}
#         fields = "__all__"
'''

_DJANGO_MIGRATION_INIT = '"""Migrations package for the {module} module."""\n'

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI stubs
# ─────────────────────────────────────────────────────────────────────────────

_FASTAPI_ROUTES = '''\
"""API routes for the {module} module."""
from fastapi import APIRouter, HTTPException
from .schemas import {module}Schema, {module}CreateSchema
from .services import {module}Service

router = APIRouter(prefix="/{module_lower}", tags=["{module_lower}"])
_service = {module}Service()


@router.get("/", response_model=list[{module}Schema])
def list_{module_lower}():
    """Return all {module} items."""
    return _service.all()


@router.get("/{{item_id}}", response_model={module}Schema)
def get_{module_lower}(item_id: int):
    """Return a single {module} item."""
    item = _service.find(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="{module} not found")
    return item


@router.post("/", response_model={module}Schema, status_code=201)
def create_{module_lower}(payload: {module}CreateSchema):
    """Create a new {module} item."""
    return _service.create(payload)
'''

_FASTAPI_SCHEMAS = '''\
"""Pydantic schemas for the {module} module."""
from pydantic import BaseModel


class {module}Schema(BaseModel):
    id: int
    name: str

    model_config = {{"from_attributes": True}}


class {module}CreateSchema(BaseModel):
    name: str
'''

_FASTAPI_SERVICES = '''\
"""Business logic / service layer for the {module} module."""
from .schemas import {module}CreateSchema, {module}Schema


class {module}Service:
    """Encapsulates all {module} business logic."""

    def all(self) -> list[{module}Schema]:
        # TODO: replace with real data source
        return []

    def find(self, item_id: int) -> {module}Schema | None:
        # TODO: replace with real data source
        return None

    def create(self, payload: {module}CreateSchema) -> {module}Schema:
        # TODO: replace with real data source
        return {module}Schema(id=1, name=payload.name)
'''

# ─────────────────────────────────────────────────────────────────────────────
# Flask stubs
# ─────────────────────────────────────────────────────────────────────────────

_FLASK_ROUTES = '''\
"""Blueprint routes for the {module} module."""
from flask import Blueprint, jsonify

blueprint = Blueprint("{module_lower}", __name__, url_prefix="/{module_lower}")


@blueprint.get("/")
def index():
    """List all {module} items."""
    return jsonify([])


@blueprint.get("/<int:item_id>")
def detail(item_id: int):
    """Return a single {module} item."""
    return jsonify({{"id": item_id, "name": "example"}})
'''

_FLASK_SERVICES = '''\
"""Business logic / service layer for the {module} module."""


class {module}Service:
    """Encapsulates all {module} business logic."""

    def all(self) -> list[dict]:
        # TODO: replace with real data source
        return []

    def find(self, item_id: int) -> dict | None:
        # TODO: replace with real data source
        return None

    def create(self, data: dict) -> dict:
        # TODO: replace with real data source
        return data
'''


# ─────────────────────────────────────────────────────────────────────────────
# Preset registry
# { relative_file_path_template: stub_content_template }
# Tokens: {module}, {module_lower}, {module_upper}, {folder}
# ─────────────────────────────────────────────────────────────────────────────

PRESETS: dict[str, dict[str, str]] = {

    "plain": {
        "module.json": _MANIFEST,
        "__init__.py": _INIT,
    },

    "default": {
        "module.json":                  _MANIFEST,
        "__init__.py":                  _INIT,
        "providers.py":                 _PROVIDER,
        "config/__init__.py":           '"""Config package for the {module} module."""\n',
        "config/config.py":             _CONFIG,
        "tests/__init__.py":            "",
        "tests/test_{module_lower}.py": _TEST,
        "assets/.gitkeep":              "",
    },

    "django": {
        "module.json":                         _MANIFEST,
        "__init__.py":                         _INIT,
        "apps.py":                             _DJANGO_APPS,
        "providers.py":                        _PROVIDER,
        "models/__init__.py":                  "from .{module_lower} import {module}  # noqa: F401\n",
        "models/{module_lower}.py":            _DJANGO_MODELS,
        "views/__init__.py":                   "",
        "views/{module_lower}_views.py":       _DJANGO_VIEWS,
        "routes.py":                           _DJANGO_ROUTES,
        "admin.py":                            _DJANGO_ADMIN,
        "serializers.py":                      _DJANGO_SERIALIZERS,
        "config/__init__.py":                  '"""Config package for the {module} module."""\n',
        "config/config.py":                    _CONFIG,
        "database/__init__.py":                "",
        "database/migrations/__init__.py":     _DJANGO_MIGRATION_INIT,
        "tests/__init__.py":                   "",
        "tests/test_{module_lower}.py":        _TEST,
        "assets/.gitkeep":                     "",
    },

    "fastapi": {
        "module.json":                  _MANIFEST,
        "__init__.py":                  _INIT,
        "providers.py":                 _PROVIDER,
        "routes.py":                    _FASTAPI_ROUTES,
        "schemas.py":                   _FASTAPI_SCHEMAS,
        "services.py":                  _FASTAPI_SERVICES,
        "config/__init__.py":           '"""Config package for the {module} module."""\n',
        "config/config.py":             _CONFIG,
        "tests/__init__.py":            "",
        "tests/test_{module_lower}.py": _TEST,
    },

    "flask": {
        "module.json":                  _MANIFEST,
        "__init__.py":                  _INIT,
        "providers.py":                 _PROVIDER,
        "routes.py":                    _FLASK_ROUTES,
        "services.py":                  _FLASK_SERVICES,
        "config/__init__.py":           '"""Config package for the {module} module."""\n',
        "config/config.py":             _CONFIG,
        "tests/__init__.py":            "",
        "tests/test_{module_lower}.py": _TEST,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────────────────────────

class ModuleGenerator:
    """
    Generates a new module scaffold inside the configured modules directory.

    preset choices: "default" | "plain" | "django" | "fastapi" | "flask"
    """

    def __init__(
        self,
        registry: "ModuleRegistry",
        *,
        preset: str = "default",
        force: bool = False,
    ) -> None:
        if preset not in PRESETS:
            raise ValueError(
                f"Unknown preset {preset!r}. "
                f"Choose from: {', '.join(PRESETS)}"
            )
        self.registry = registry
        self.preset = preset
        self.force = force

    def generate(self, name: str) -> Path:
        """
        Create a new module named *name* under the registry's modules root.

        Returns the path of the created module directory.
        Raises ModuleAlreadyExistsError if the module already exists and
        force=False.
        """
        name = self._normalise_name(name)
        dest = self.registry.modules_root / name

        if dest.exists():
            if not self.force:
                raise ModuleAlreadyExistsError(name)
            shutil.rmtree(dest)

        dest.mkdir(parents=True)

        # {folder} = the last segment of modules_root (e.g. "plugins", "apps")
        # injected into module.json providers path so it's always correct
        # regardless of what the user named their folder.
        folder = self.registry.modules_root.name

        replacements = {
            "module":       name,
            "module_lower": name.lower(),
            "module_upper": name.upper(),
            "folder":       folder,
        }

        for rel_template, content_template in PRESETS[self.preset].items():
            rel_path = rel_template.format(**replacements)
            file_path = dest / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content_template.format(**replacements))

        self.registry.scan()
        return dest

    @staticmethod
    def _normalise_name(name: str) -> str:
        """Ensure the module name is PascalCase."""
        return name[0].upper() + name[1:] if name else name
