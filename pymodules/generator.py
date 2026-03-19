"""
ModuleGenerator — creates a new module scaffold on disk.

Presets:
  - "plain"        : module.json + __init__.py only
  - "default"      : framework-agnostic (providers, config, tests)
  - "django"       : HTML views, models, admin, migrations
  - "django-api"   : DRF REST API (ViewSet, Serializer, api/urls.py, Router)
  - "fastapi"      : APIRouter with 3-endpoint CRUD skeleton
  - "fastapi-crud" : APIRouter with full 5-endpoint CRUD (list/get/create/update/delete)
  - "flask"        : Blueprint with service layer
  - "flask-api"    : Blueprint REST API (JSON, full CRUD, service layer)
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
# Django HTML stubs  (django preset)
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
"""HTML views for the {module} module."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404

# from ..models.{module_lower} import {module}


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

# from .models.{module_lower} import {module}

# @admin.register({module})
# class {module}Admin(admin.ModelAdmin):
#     list_display = ("name", "created_at")
#     search_fields = ("name",)
'''

_DJANGO_SERIALIZERS_COMMENTED = '''\
"""DRF serializers for the {module} module (requires djangorestframework)."""
# from rest_framework import serializers
# from .models.{module_lower} import {module}

# class {module}Serializer(serializers.ModelSerializer):
#     class Meta:
#         model = {module}
#         fields = "__all__"
'''

_DJANGO_MIGRATION_INIT = '"""Migrations package for the {module} module."""\n'


# ─────────────────────────────────────────────────────────────────────────────
# Django REST API stubs  (django-api preset)
# ─────────────────────────────────────────────────────────────────────────────

_DJANGO_API_SERIALIZER = '''\
"""DRF serializers for the {module} module."""
from rest_framework import serializers

from .models.{module_lower} import {module}


class {module}Serializer(serializers.ModelSerializer):
    """Full serializer — used for create/update."""

    class Meta:
        model = {module}
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class {module}ListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints."""

    class Meta:
        model = {module}
        fields = ("id", "name", "created_at")
'''

_DJANGO_API_VIEWSET = '''\
"""DRF ViewSet for the {module} module."""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models.{module_lower} import {module}
from .serializers import {module}Serializer, {module}ListSerializer


class {module}ViewSet(viewsets.ModelViewSet):
    """
    REST API endpoint for {module}.

    list:        GET  /{module_lower}/
    retrieve:    GET  /{module_lower}/{{id}}/
    create:      POST /{module_lower}/
    update:      PUT  /{module_lower}/{{id}}/
    partial:     PATCH /{module_lower}/{{id}}/
    destroy:     DELETE /{module_lower}/{{id}}/
    """

    queryset = {module}.objects.all().order_by("-created_at")
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return {module}ListSerializer
        return {module}Serializer
'''

_DJANGO_API_URLS = '''\
"""API URL configuration for the {module} module.

Registered automatically by DjangoModuleRegistry.api_url_patterns()
at the prefix defined by `api_prefix` below.
"""
from rest_framework.routers import DefaultRouter

from .viewsets import {module}ViewSet

# Mounted at: /api/{module_lower}/  (via DjangoModuleRegistry.api_url_patterns)
api_prefix = "{module_lower}"

router = DefaultRouter()
router.register(r"", {module}ViewSet, basename="{module_lower}")

urlpatterns = router.urls
'''

_DJANGO_API_ROUTES = '''\
"""Standard URL configuration for the {module} module.

Thin wrapper — delegates to api/urls.py so both
  url_patterns()      (mounted at /{module_lower}/)
  api_url_patterns()  (mounted at /api/{module_lower}/)
work correctly.
"""
from django.urls import include, path

from .api.urls import urlpatterns as api_urlpatterns

prefix = "{module_lower}"
app_name = "{module_lower}"

# Re-export API urls so url_patterns() also picks them up if desired
urlpatterns = [
    path("", include(api_urlpatterns)),
]
'''


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI stubs  (fastapi preset — 3 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

_FASTAPI_ROUTES = '''\
"""API routes for the {module} module."""
from fastapi import APIRouter, HTTPException

from .schemas import {module}Schema, {module}CreateSchema
from .services import {module}Service

router = APIRouter(prefix="/{module_lower}", tags=["{module_lower}"])
_service = {module}Service()


@router.get("/", response_model=list[{module}Schema], summary="List all {module} items")
def list_{module_lower}():
    return _service.all()


@router.get("/{{item_id}}", response_model={module}Schema, summary="Get a single {module}")
def get_{module_lower}(item_id: int):
    item = _service.find(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="{module} not found")
    return item


@router.post("/", response_model={module}Schema, status_code=201, summary="Create a {module}")
def create_{module_lower}(payload: {module}CreateSchema):
    return _service.create(payload)
'''

_FASTAPI_SCHEMAS = '''\
"""Pydantic schemas for the {module} module."""
from pydantic import BaseModel


class {module}Schema(BaseModel):
    """Response schema — returned by all read endpoints."""
    id: int
    name: str

    model_config = {{"from_attributes": True}}


class {module}CreateSchema(BaseModel):
    """Request schema for POST /."""
    name: str


class {module}UpdateSchema(BaseModel):
    """Request schema for PUT / PATCH — all fields optional."""
    name: str | None = None
'''

_FASTAPI_SERVICES = '''\
"""Business logic / service layer for the {module} module."""
from .schemas import {module}CreateSchema, {module}Schema, {module}UpdateSchema


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

    def update(self, item_id: int, payload: {module}UpdateSchema) -> {module}Schema | None:
        # TODO: replace with real data source
        return None

    def delete(self, item_id: int) -> bool:
        # TODO: replace with real data source
        return False
'''


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI CRUD stubs  (fastapi-crud preset — full 5 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

_FASTAPI_CRUD_ROUTES = '''\
"""Full CRUD API routes for the {module} module."""
from fastapi import APIRouter, HTTPException, status

from .schemas import {module}Schema, {module}CreateSchema, {module}UpdateSchema
from .services import {module}Service

router = APIRouter(prefix="/{module_lower}", tags=["{module_lower}"])
_service = {module}Service()


@router.get(
    "/",
    response_model=list[{module}Schema],
    summary="List all {module} items",
)
def list_{module_lower}():
    """Return all {module} items."""
    return _service.all()


@router.get(
    "/{{item_id}}",
    response_model={module}Schema,
    summary="Retrieve a {module}",
)
def get_{module_lower}(item_id: int):
    """Return a single {module} by ID."""
    item = _service.find(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="{module} not found")
    return item


@router.post(
    "/",
    response_model={module}Schema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a {module}",
)
def create_{module_lower}(payload: {module}CreateSchema):
    """Create a new {module}."""
    return _service.create(payload)


@router.put(
    "/{{item_id}}",
    response_model={module}Schema,
    summary="Replace a {module}",
)
def update_{module_lower}(item_id: int, payload: {module}UpdateSchema):
    """Fully replace an existing {module}."""
    item = _service.update(item_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="{module} not found")
    return item


@router.delete(
    "/{{item_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a {module}",
)
def delete_{module_lower}(item_id: int):
    """Permanently delete a {module}."""
    if not _service.delete(item_id):
        raise HTTPException(status_code=404, detail="{module} not found")
'''


# ─────────────────────────────────────────────────────────────────────────────
# Flask stubs  (flask preset)
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
# Flask REST API stubs  (flask-api preset — full CRUD)
# ─────────────────────────────────────────────────────────────────────────────

_FLASK_API_ROUTES = '''\
"""REST API Blueprint for the {module} module."""
from flask import Blueprint, jsonify, request, abort

from .services import {module}Service

blueprint = Blueprint("{module_lower}_api", __name__, url_prefix="/api/{module_lower}")
_service = {module}Service()


@blueprint.get("/")
def list_{module_lower}():
    """GET /api/{module_lower}/ — list all items."""
    return jsonify(_service.all()), 200


@blueprint.get("/<int:item_id>")
def get_{module_lower}(item_id: int):
    """GET /api/{module_lower}/{{item_id}} — retrieve one item."""
    item = _service.find(item_id)
    if item is None:
        abort(404, description="{module} not found")
    return jsonify(item), 200


@blueprint.post("/")
def create_{module_lower}():
    """POST /api/{module_lower}/ — create a new item."""
    data = request.get_json(force=True, silent=True) or {{}}
    item = _service.create(data)
    return jsonify(item), 201


@blueprint.put("/<int:item_id>")
def update_{module_lower}(item_id: int):
    """PUT /api/{module_lower}/{{item_id}} — replace an item."""
    data = request.get_json(force=True, silent=True) or {{}}
    item = _service.update(item_id, data)
    if item is None:
        abort(404, description="{module} not found")
    return jsonify(item), 200


@blueprint.delete("/<int:item_id>")
def delete_{module_lower}(item_id: int):
    """DELETE /api/{module_lower}/{{item_id}} — remove an item."""
    if not _service.delete(item_id):
        abort(404, description="{module} not found")
    return "", 204
'''

_FLASK_API_SERVICES = '''\
"""Business logic / service layer for the {module} module."""


class {module}Service:
    """Encapsulates all {module} REST API business logic."""

    def all(self) -> list[dict]:
        # TODO: replace with real data source
        return []

    def find(self, item_id: int) -> dict | None:
        # TODO: replace with real data source
        return None

    def create(self, data: dict) -> dict:
        # TODO: replace with real data source
        return data

    def update(self, item_id: int, data: dict) -> dict | None:
        # TODO: replace with real data source
        return None

    def delete(self, item_id: int) -> bool:
        # TODO: replace with real data source
        return False
'''

_FLASK_API_TEST = '''\
"""Tests for the {module} REST API module."""
import pytest


class Test{module}Api:
    def test_list_returns_200(self, client):
        response = client.get("/api/{module_lower}/")
        assert response.status_code == 200

    def test_get_missing_returns_404(self, client):
        response = client.get("/api/{module_lower}/999")
        assert response.status_code == 404

    def test_create_returns_201(self, client):
        response = client.post("/api/{module_lower}/", json={{"name": "test"}})
        assert response.status_code == 201
'''


# ─────────────────────────────────────────────────────────────────────────────
# Django API test stub
# ─────────────────────────────────────────────────────────────────────────────

_DJANGO_API_TEST = '''\
"""Tests for the {module} REST API module."""
import pytest

# Requires: pip install pytest-django


class Test{module}Api:
    def test_list_returns_200(self, client):
        response = client.get("/api/{module_lower}/")
        assert response.status_code == 200

    def test_create_returns_201(self, client):
        response = client.post(
            "/api/{module_lower}/",
            data='{{"name": "test"}}',
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_get_missing_returns_404(self, client):
        response = client.get("/api/{module_lower}/999/")
        assert response.status_code == 404
'''


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI API test stub
# ─────────────────────────────────────────────────────────────────────────────

_FASTAPI_TEST = '''\
"""Tests for the {module} API module."""
import pytest
from fastapi.testclient import TestClient


class Test{module}Api:
    def test_list_returns_200(self, client: TestClient):
        response = client.get("/{module_lower}/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_returns_201(self, client: TestClient):
        response = client.post("/{module_lower}/", json={{"name": "test"}})
        assert response.status_code == 201

    def test_get_missing_returns_404(self, client: TestClient):
        response = client.get("/{module_lower}/999")
        assert response.status_code == 404
'''


# ─────────────────────────────────────────────────────────────────────────────
# Preset registry
# ─────────────────────────────────────────────────────────────────────────────

PRESETS: dict[str, dict[str, str]] = {

    # ── plain ────────────────────────────────────────────────────────────────
    "plain": {
        "module.json": _MANIFEST,
        "__init__.py": _INIT,
    },

    # ── default ──────────────────────────────────────────────────────────────
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

    # ── django (HTML views) ───────────────────────────────────────────────────
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
        "serializers.py":                      _DJANGO_SERIALIZERS_COMMENTED,
        "config/__init__.py":                  '"""Config package for the {module} module."""\n',
        "config/config.py":                    _CONFIG,
        "database/__init__.py":                "",
        "database/migrations/__init__.py":     _DJANGO_MIGRATION_INIT,
        "tests/__init__.py":                   "",
        "tests/test_{module_lower}.py":        _TEST,
        "assets/.gitkeep":                     "",
    },

    # ── django-api (DRF REST API) ─────────────────────────────────────────────
    "django-api": {
        "module.json":                         _MANIFEST,
        "__init__.py":                         _INIT,
        "apps.py":                             _DJANGO_APPS,
        "providers.py":                        _PROVIDER,
        "models/__init__.py":                  "from .{module_lower} import {module}  # noqa: F401\n",
        "models/{module_lower}.py":            _DJANGO_MODELS,
        "serializers.py":                      _DJANGO_API_SERIALIZER,
        "viewsets.py":                         _DJANGO_API_VIEWSET,
        "api/__init__.py":                     "",
        "api/urls.py":                         _DJANGO_API_URLS,
        "routes.py":                           _DJANGO_API_ROUTES,
        "admin.py":                            _DJANGO_ADMIN,
        "config/__init__.py":                  '"""Config package for the {module} module."""\n',
        "config/config.py":                    _CONFIG,
        "database/__init__.py":                "",
        "database/migrations/__init__.py":     _DJANGO_MIGRATION_INIT,
        "tests/__init__.py":                   "",
        "tests/test_{module_lower}.py":        _DJANGO_API_TEST,
        "assets/.gitkeep":                     "",
    },

    # ── fastapi (3-endpoint) ──────────────────────────────────────────────────
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
        "tests/test_{module_lower}.py": _FASTAPI_TEST,
    },

    # ── fastapi-crud (5-endpoint) ─────────────────────────────────────────────
    "fastapi-crud": {
        "module.json":                  _MANIFEST,
        "__init__.py":                  _INIT,
        "providers.py":                 _PROVIDER,
        "routes.py":                    _FASTAPI_CRUD_ROUTES,
        "schemas.py":                   _FASTAPI_SCHEMAS,
        "services.py":                  _FASTAPI_SERVICES,
        "config/__init__.py":           '"""Config package for the {module} module."""\n',
        "config/config.py":             _CONFIG,
        "tests/__init__.py":            "",
        "tests/test_{module_lower}.py": _FASTAPI_TEST,
    },

    # ── flask (HTML/basic JSON) ───────────────────────────────────────────────
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

    # ── flask-api (full REST CRUD) ────────────────────────────────────────────
    "flask-api": {
        "module.json":                  _MANIFEST,
        "__init__.py":                  _INIT,
        "providers.py":                 _PROVIDER,
        "routes.py":                    _FLASK_API_ROUTES,
        "services.py":                  _FLASK_API_SERVICES,
        "config/__init__.py":           '"""Config package for the {module} module."""\n',
        "config/config.py":             _CONFIG,
        "tests/__init__.py":            "",
        "tests/test_{module_lower}.py": _FLASK_API_TEST,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────────────────────────

class ModuleGenerator:
    """
    Generates a new module scaffold inside the configured modules directory.

    preset choices:
        plain | default | django | django-api | fastapi | fastapi-crud | flask | flask-api
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

        Returns the created module directory path.
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
