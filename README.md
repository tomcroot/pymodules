# pymodules

> Modular application architecture for Python — inspired by Laravel Modules, built for the Python ecosystem.

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/tomcroot/pymodules)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](https://github.com/tomcroot/pymodules)

`pymodules` lets you split large Python applications into self-contained, independently toggleable **modules** — each with its own models, views, routes, config, migrations, service providers, and tests. It works with any Python project and ships with first-class support for **Django**, **Flask**, and **FastAPI**.

---

## Table of Contents

- [Why pymodules?](#why-pymodules)
- [Version 0.1.0](#version-010)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Module Structure](#module-structure)
- [The module.json Manifest](#the-modulejson-manifest)
- [CLI Reference — pymodules](#cli-reference--pymodules)
- [Framework Detection](#framework-detection)
- [Scaffold Presets](#scaffold-presets)
- [Service Providers](#service-providers)
- [Django Integration](#django-integration)
- [Flask Integration](#flask-integration)
- [FastAPI Integration](#fastapi-integration)
- [Pure Python Usage](#pure-python-usage)
- [Project Configuration — pymodules.toml](#project-configuration--pymodulestoml)
- [API Reference](#api-reference)
- [Feature Status](#feature-status)
- [Release Process](#release-process)
- [Roadmap to Industry Standard](#roadmap-to-industry-standard)
- [Contributing](#contributing)
- [License](#license)

---

## Why pymodules?

A typical Django or FastAPI project starts flat and becomes a maze:

```
myproject/
    models.py          # 800 lines, everything mixed together
    views.py           # 1200 lines
    urls.py            # references all 40 views
    settings.py        # references everything
```

`pymodules` enforces a boundary-first architecture. Every feature is a module:

```
myproject/
    modules/
        Blog/           # completely self-contained
        Shop/           # independent — can be disabled with one line
        Auth/           # has its own models, routes, config, migrations
        Notifications/
```

Each module is a Python package that can be **enabled or disabled at runtime** by flipping a flag in its `module.json`. Disabled modules are not imported, not booted, and not registered with your framework.

This is the Python equivalent of [nWidart/laravel-modules](https://github.com/nWidart/laravel-modules) — the most popular Laravel package for large application architecture.

---

## Version 0.1.0

This is the **first public release** of pymodules. It is production-usable for greenfield projects and stable enough for evaluation in existing projects.

**What 0.1.0 delivers:**

- Framework-agnostic core (`ModuleRegistry`, `Module`, `ServiceProvider`)
- Auto-detection of Django, FastAPI, Flask from your environment
- `pymodules` CLI with `init`, `make`, `list`, `enable`, `disable`, `show`, `delete`, `publish`, `detect`, `presets`
- Django `manage.py` integration (`module_make`, `module_list`, `module_enable`, `module_disable`, `module_show`, `module_delete`, `module_publish`)
- Eight scaffold presets: `plain`, `default`, `django`, `django-api`, `fastapi`, `fastapi-crud`, `flask`, `flask-api`
- Per-project config via `pymodules.toml`
- Custom folder naming — call it `modules/`, `plugins/`, `apps/`, `src/features/` — anything
- Module manifest (`module.json`) with versioning, enable/disable, provider registration
- Service Provider pattern for boot-time registration logic
- Module-level settings merged into Django settings
- Module-level URL routing for all three frameworks
- Module-level migrations for Django
- Asset publishing system

---

## Installation

```bash
# Core — no framework dependencies (pure Python, FastAPI, Flask)
pip install pytmodules

# With Django support
pip install "pytmodules[django]"

# With Django + Django REST Framework scaffolding support
pip install "pytmodules[django-api]"

# With Flask support
pip install "pytmodules[flask]"

# With FastAPI support
pip install "pytmodules[fastapi]"

# Everything
pip install "pytmodules[django,flask,fastapi]"
```

**From GitHub (development installs):**

```bash
pip install git+https://github.com/tomcroot/pymodules.git
pip install "pytmodules[django] @ git+https://github.com/tomcroot/pymodules.git"
```

**Requirements:** Python 3.10+

## Release Process

Releases are automated with GitHub Actions:

- [.github/workflows/release.yml](.github/workflows/release.yml) (manual trigger) bumps version files, creates/pushes a `v*` tag, and creates the GitHub Release.
- [.github/workflows/publish.yml](.github/workflows/publish.yml) runs on tag push (`v*`), builds artifacts, runs `twine check`, and publishes to PyPI via trusted publishing.

Local validation before cutting a release:

```bash
python -m build
python -m twine check dist/*
```

Release flow:

1. Ensure `CHANGELOG.md` has release-ready notes under `[Unreleased]`.
2. Run the **Release** workflow from GitHub Actions (`workflow_dispatch`) and provide the version (for example, `0.1.1`).
3. The workflow updates version metadata, commits, tags (`v0.1.1`), and creates the GitHub Release.
4. Tag push automatically triggers the publish workflow, which builds and uploads to PyPI.

The publish workflow is configured for PyPI trusted publishing. Keep the GitHub `pypi` environment and PyPI trusted publisher settings in sync if repository, workflow, or environment names change.

---

## Quick Start

### Any Python project

```bash
cd myproject
pymodules init          # auto-detects your framework, creates pymodules.toml
pymodules make Blog     # scaffold a Blog module using detected framework
```

### Django project

```bash
pip install "pytmodules[django]"
pymodules init          # detects Django, writes pymodules.toml
pymodules make Blog     # creates full Django module scaffold

# Or with manage.py (once "pymodules" is in INSTALLED_APPS):
python manage.py module_make Blog
```

### FastAPI project

```bash
pip install "pytmodules[fastapi]"
pymodules init
pymodules make Blog     # creates FastAPI module with APIRouter + Pydantic schemas
```

### Flask project

```bash
pip install "pytmodules[flask]"
pymodules init
pymodules make Blog     # creates Flask module with Blueprint
```

---

## Module Structure

Every module is a Python package directory inside your modules folder. The layout depends on the scaffold preset used, but the full structure (from the `django` preset) is:

```
modules/
└── Blog/
    ├── module.json               ← required: manifest, version, enabled flag, providers
    ├── __init__.py
    ├── apps.py                   ← Django AppConfig (django preset)
    ├── providers.py              ← ServiceProvider subclass
    ├── routes.py                 ← URL patterns / Blueprint / APIRouter
    ├── admin.py                  ← Django admin registration (django preset)
    ├── serializers.py            ← DRF serializers, commented (django preset)
    ├── schemas.py                ← Pydantic schemas (fastapi preset)
    ├── services.py               ← Business logic layer (fastapi/flask presets)
    ├── models/
    │   ├── __init__.py
    │   └── blog.py               ← Django model (django preset)
    ├── views/
    │   ├── __init__.py
    │   └── blog_views.py         ← Django views (django preset)
    ├── config/
    │   ├── __init__.py
    │   └── config.py             ← Module-level settings (all presets)
    ├── database/
    │   └── migrations/           ← Django migrations (django preset)
    │       └── __init__.py
    ├── assets/                   ← Publishable static files
    └── tests/
        ├── __init__.py
        └── test_blog.py          ← Starter test class
```

---

## The module.json Manifest

Every module has a `module.json` at its root. This is the single source of truth for the module's identity and state.

```json
{
    "name": "Blog",
    "version": "1.0.0",
    "description": "Blog module with posts, tags and comments.",
    "author": "Your Name",
    "enabled": true,
    "requires": ["Core"],
    "providers": [
        "modules.Blog.providers.BlogServiceProvider"
    ],
    "publishes": {
        "default": {
            "assets/blog.css": "static/blog/blog.css"
        },
        "config": {
            "config/config.py": "config/blog_config.py"
        }
    }
}
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Module name (PascalCase) |
| `version` | No | Semantic version string |
| `description` | No | Human-readable description |
| `author` | No | Author name or email |
| `enabled` | Yes | `true`/`false` — controls whether the module boots |
| `requires` | No | List of module names that must boot before this module |
| `providers` | No | Dotted paths to ServiceProvider subclasses |
| `publishes` | No | Asset publish map (group → source → destination) |

---

## CLI Reference — pymodules

The `pymodules` CLI is available after installation. All commands read `pymodules.toml` for defaults.

### `pymodules init`

Initialise pymodules in a project. Auto-detects your framework and writes `pymodules.toml`.

```bash
pymodules init                             # fully automatic
pymodules init --path plugins              # custom folder name
pymodules init --path apps --preset django # explicit preset
pymodules init --force                     # overwrite existing config
```

### `pymodules detect`

Show which framework was detected and why.

```bash
pymodules detect
pymodules detect --path /other/project
```

Output:

```
  Framework  : django
  Preset     : django
  Confidence : high
  Reason     : django is installed in the active Python environment;
               found django-specific project files (manage.py)
```

### `pymodules make`

Create a new module scaffold.

```bash
pymodules make Blog                        # auto-detected preset
pymodules make Blog --preset django        # explicit preset
pymodules make Blog --preset fastapi
pymodules make Blog --preset flask
pymodules make Blog --preset plain         # bare minimum
pymodules make Blog --force                # overwrite existing
```

### `pymodules list`

List all modules and their status.

```bash
pymodules list
pymodules list --enabled-only
pymodules list --disabled-only
```

### `pymodules enable` / `pymodules disable`

Toggle a module on or off. Writes to `module.json` — persists across restarts.

```bash
pymodules enable  Blog
pymodules disable Blog
```

### `pymodules show`

Show full details for a single module.

```bash
pymodules show Blog
```

### `pymodules delete`

Delete a module from disk.

```bash
pymodules delete Blog
pymodules delete Blog --yes    # skip confirmation
```

### `pymodules publish`

Copy a module's publishable assets to the host application.

```bash
pymodules publish Blog
pymodules publish Blog --group config
pymodules publish              # publish all enabled modules
pymodules publish --force      # overwrite existing files
```

### `pymodules presets`

List all available scaffold presets.

```bash
pymodules presets
```

### Global options

```bash
pymodules --modules-path src/apps make Blog   # override modules folder
```

Set `PYMODULES_PATH` environment variable to avoid passing `--modules-path` on every command.

---

## Framework Detection

`pymodules` detects your framework automatically using a three-layer strategy:

| Layer | Method | Confidence boost |
|---|---|---|
| 1 | `importlib.util.find_spec()` — is the package installed in this venv? | +10 |
| 1b | `DJANGO_SETTINGS_MODULE` environment variable set? | +5 (Django only) |
| 2 | Project file fingerprints (`manage.py`, `wsgi.py`, `app.py` …) | +3 |
| 3 | Dependency file scanning (`requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.cfg`) | +2 |

When multiple frameworks are detected, priority is **Django > FastAPI > Flask**.

Use the detector in your own code:

```python
from pymodules import detect_framework

info = detect_framework()
print(info.name)        # "django" | "fastapi" | "flask" | "unknown"
print(info.confidence)  # "high" | "medium" | "low"
print(info.preset)      # matching preset name
print(info.reason)      # human-readable explanation
```

---

## Scaffold Presets

Presets control exactly which files are generated by `pymodules make`.

### `plain`
Bare minimum. Use when you want to build your own structure.
```
Blog/
  module.json
  __init__.py
```

### `default`
Framework-agnostic. A clean starting point for any Python project.
```
Blog/
  module.json, __init__.py, providers.py
  config/config.py
  tests/test_blog.py
  assets/
```

### `django`
Full Django module. Everything you need to add a new bounded context.
```
Blog/
  module.json, __init__.py, apps.py, providers.py
  models/blog.py          ← ready-to-use Django model
  views/blog_views.py     ← index + detail views
  routes.py               ← urlpatterns + prefix
  admin.py                ← commented ModelAdmin
  serializers.py          ← commented DRF serializer
  config/config.py
  database/migrations/__init__.py
  tests/test_blog.py
  assets/
```

### `django-api`
Django REST module with DRF serializer, viewset, and router wiring.
```
Blog/
    module.json, __init__.py, apps.py, providers.py
    models/blog.py
    serializers.py      ← DRF ModelSerializer + ListSerializer
    policies.py         ← DRF AccessPolicy scaffold for API permissions
    viewsets.py         ← DRF ModelViewSet
    api/urls.py         ← DefaultRouter wiring
    routes.py           ← thin wrapper delegating to api/urls.py
    admin.py
    config/config.py
    database/migrations/__init__.py
    tests/test_blog.py
    assets/
```

### `fastapi`
FastAPI module with 3-endpoint API skeleton.
```
Blog/
  module.json, __init__.py, providers.py
  routes.py       ← APIRouter with list/get/create endpoints
  schemas.py      ← Pydantic BaseModel (Schema + CreateSchema)
  services.py     ← Service class (business logic layer)
  config/config.py
  tests/test_blog.py
```

### `fastapi-crud`
FastAPI module with full CRUD endpoints.
```
Blog/
    module.json, __init__.py, providers.py
    routes.py       ← APIRouter with list/get/create/update/delete endpoints
    schemas.py      ← Schema + CreateSchema + UpdateSchema
    services.py     ← includes update() and delete() skeletons
    config/config.py
    tests/test_blog.py
```

### `flask`
Flask module with Blueprint.
```
Blog/
  module.json, __init__.py, providers.py
  routes.py       ← Blueprint with index + detail routes
  services.py     ← Service class
  config/config.py
  tests/test_blog.py
```

### `flask-api`
Flask module with JSON REST CRUD endpoints.
```
Blog/
    module.json, __init__.py, providers.py
    routes.py       ← /api/{module}/ CRUD Blueprint
    services.py     ← all/create/find/update/delete skeletons
    config/config.py
    tests/test_blog.py
```

---

## Service Providers

Service providers run arbitrary boot logic when a module is loaded. They are the correct place to register signals, middleware, event listeners, DI bindings, or any other setup that needs to run once at startup.

```python
# modules/Blog/providers.py
from pymodules import ServiceProvider

class BlogServiceProvider(ServiceProvider):

    def register(self) -> None:
        """
        Called during module boot.
        Register bindings, connect signals, set up DI.
        """
        from django.db.models.signals import post_save
        from .models.blog import Post
        from .listeners import on_post_saved
        post_save.connect(on_post_saved, sender=Post)

    def boot(self) -> None:
        """
        Called after all modules have registered.
        Use for setup that depends on other modules.
        """
        pass
```

Reference providers in `module.json`:

```json
{
    "providers": [
        "modules.Blog.providers.BlogServiceProvider"
    ]
}
```

---

## Django Integration

### settings.py

```python
from pathlib import Path
from pymodules.integrations.django import DjangoModuleRegistry

BASE_DIR = Path(__file__).resolve().parent.parent

MODULE_REGISTRY = DjangoModuleRegistry(modules_path=BASE_DIR / "modules")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    # ...

    "pymodules",                          # registers manage.py module_* commands
    *MODULE_REGISTRY.installed_apps(),    # auto-registers all enabled modules
]

# Point Django to each module's own migrations folder
MIGRATION_MODULES = MODULE_REGISTRY.migration_modules()

# Merge UPPER_CASE variables from every module's config/config.py
locals().update(MODULE_REGISTRY.collect_settings())
```

### urls.py

```python
from django.contrib import admin
from django.urls import path
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    *settings.MODULE_REGISTRY.url_patterns(),   # auto-includes all module routes
    *settings.MODULE_REGISTRY.api_url_patterns(),   # auto-includes /api/<module>/ routes
]
```

### Module routes.py

```python
# modules/Blog/routes.py
from django.urls import path
from .views.blog_views import index, detail

prefix = "blog"     # mounted at /blog/

app_name = "blog"

urlpatterns = [
    path("", index, name="index"),
    path("<int:pk>/", detail, name="detail"),
]
```

### Module-level settings

```python
# modules/Blog/config/config.py
BLOG_POSTS_PER_PAGE = 10
BLOG_ALLOW_COMMENTS = True
BLOG_CACHE_TTL = 300
```

These are automatically merged into Django settings via `collect_settings()`.

### API permissions with `collect_policies()`

For DRF-based modules, `DjangoModuleRegistry.collect_policies()` auto-discovers
`AccessPolicy` subclasses from enabled modules. This is library-level plumbing:
`pymodules` handles discovery and naming conventions, while each application
keeps its actual permission rules inside its own modules.

`collect_policies()` supports either:

- a flat `policies.py` file for simple modules
- a `policies/` package for larger modules

Example `settings.py` usage:

```python
from pathlib import Path
from pymodules.integrations.django import DjangoModuleRegistry

BASE_DIR = Path(__file__).resolve().parent.parent
MODULE_REGISTRY = DjangoModuleRegistry(modules_path=BASE_DIR / "modules")

MODULE_POLICIES = MODULE_REGISTRY.collect_policies()
```

Example `django-api` scaffold output:

```python
# modules/Blog/policies.py
from rest_framework_access_policy import AccessPolicy


class BlogPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ]
```

Direct binding inside a DRF viewset:

```python
from rest_framework import viewsets

from .models.blog import Blog
from .policies import BlogPolicy
from .serializers import BlogSerializer


class BlogViewSet(viewsets.ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [BlogPolicy]
```

Registry lookup when you want indirection:

```python
from django.conf import settings

BlogPolicy = settings.MODULE_REGISTRY.get_policy("modules.Blog.policies.BlogPolicy")
```

If you use a `policies/` package, keys reflect the real import path, for example
`modules.HR.policies.employee.EmployeePolicy`.

This feature requires `drf-access-policy`, which is included in
`pytmodules[django-api]`.

### manage.py commands

Once `"pymodules"` is in `INSTALLED_APPS`, all `module_*` commands are available:

```bash
python manage.py module_make   Blog
python manage.py module_make   Blog --preset django
python manage.py module_make   Blog --force
python manage.py module_list
python manage.py module_list   --enabled
python manage.py module_list   --disabled
python manage.py module_show   Blog
python manage.py module_enable  Blog
python manage.py module_disable Blog
python manage.py module_delete  Blog
python manage.py module_delete  Blog --yes
python manage.py module_publish Blog
python manage.py module_publish Blog --group config
python manage.py module_publish --force
python manage.py module_make_model Blog Post
python manage.py module_make_model Blog ArchivedPost --proxy --parent Post
python manage.py module_make_serializer Blog Post
python manage.py module_make_viewset Blog Post
python manage.py module_make_api_urls Blog
python manage.py module_make_model_migration Blog Post --auto-name
python manage.py module_make_migration Blog
python manage.py module_migrate Blog
```

`module_make` without `--preset` defaults to `"django"` when running via `manage.py` — because the fact that you're using `manage.py` is itself proof this is a Django project.

---

## Flask Integration

```python
from flask import Flask
from pymodules.integrations.flask import FlaskModuleRegistry

app = Flask(__name__)
registry = FlaskModuleRegistry(modules_path="modules", app=app)
registry.boot()  # auto-registers all enabled module Blueprints
```

**App factory pattern:**

```python
registry = FlaskModuleRegistry(modules_path="modules")

def create_app():
    app = Flask(__name__)
    registry.init_app(app)  # boots and registers Blueprints
    return app
```

**Module routes.py:**

```python
# modules/Blog/routes.py
from flask import Blueprint, jsonify

blueprint = Blueprint("blog", __name__, url_prefix="/blog")

@blueprint.get("/")
def index():
    return jsonify([])
```

---

## FastAPI Integration

```python
from fastapi import FastAPI
from pymodules.integrations.fastapi import FastAPIModuleRegistry

app = FastAPI()
registry = FastAPIModuleRegistry(modules_path="modules", app=app)
registry.boot()  # auto-includes all enabled module APIRouters
```

**App factory pattern:**

```python
registry = FastAPIModuleRegistry(modules_path="modules")

def create_app():
    app = FastAPI()
    registry.init_app(app)
    return app
```

**Module routes.py:**

```python
# modules/Blog/routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/blog", tags=["blog"])

@router.get("/")
def index():
    return {"message": "Blog index"}
```

---

## Pure Python Usage

No framework required. Use `ModuleRegistry` directly:

```python
from pymodules import ModuleRegistry

registry = ModuleRegistry(modules_path="modules")
registry.boot()

# Find a module
blog = registry.find("Blog")
print(blog.name, blog.version, blog.is_enabled)

# Enable / disable (writes to module.json)
registry.enable("Shop")
registry.disable("Blog")

# Iterate
for module in registry:
    print(module)

# Check existence
if "Blog" in registry:
    print("Blog module is registered")

# Boot hooks — run for every enabled module at boot time
@registry.on_boot
def on_module_boot(module):
    print(f"Booted: {module.name}")

# Import a submodule
models = blog.import_submodule("models.post")
```

---

## Project Configuration — pymodules.toml

`pymodules.toml` lives at your project root and is committed to version control. It means you and your team never have to pass `--modules-path` manually.

```toml
# pymodules.toml
[pymodules]

# Where your modules/plugins live.
# Can be any name: "modules", "plugins", "apps", "src/features", etc.
modules_path = "modules"

# Default scaffold preset for `pymodules make` and `manage.py module_make`.
# Auto-detected from your environment — change if detection is wrong.
# Choices: default | plain | django | fastapi | flask
default_preset = "django"

# Informational — set by `pymodules init`, not read by the tool.
detected_framework = "django"
```

**Config resolution order** (highest priority first):

1. `--modules-path` / `--preset` CLI flags
2. `pymodules.toml` values
3. Auto-detected framework
4. Hardcoded fallbacks (`"modules"` / `"default"`)

---

## API Reference

### `ModuleRegistry`

```python
from pymodules import ModuleRegistry

registry = ModuleRegistry(
    modules_path="modules",   # str or Path
    scan_on_init=True,        # auto-scan on construction
)
```

| Method / Property | Returns | Description |
|---|---|---|
| `registry.all()` | `list[Module]` | All modules (enabled + disabled) |
| `registry.all_enabled()` | `list[Module]` | Only enabled modules |
| `registry.all_disabled()` | `list[Module]` | Only disabled modules |
| `registry.find(name)` | `Module` | Find by name, raises `ModuleNotFoundError` |
| `registry.exists(name)` | `bool` | Check if a module exists |
| `registry.count()` | `int` | Total number of modules |
| `registry.enable(name)` | `None` | Enable a module (persists to disk) |
| `registry.disable(name)` | `None` | Disable a module (persists to disk) |
| `registry.boot()` | `None` | Boot all enabled modules |
| `registry.scan()` | `None` | Re-scan the modules directory |
| `registry.module_path(name, *parts)` | `Path` | Resolve path within a module |
| `registry.on_boot(fn)` | `fn` | Register a boot hook (decorator) |
| `"Blog" in registry` | `bool` | Membership test |
| `for m in registry` | — | Iteration |

### `Module`

| Property / Method | Returns | Description |
|---|---|---|
| `module.name` | `str` | Module name |
| `module.path` | `Path` | Absolute path to module directory |
| `module.import_path` | `str` | Dotted Python import path |
| `module.is_enabled` | `bool` | Current enabled state |
| `module.enable()` | `None` | Enable (writes `module.json`) |
| `module.disable()` | `None` | Disable (writes `module.json`) |
| `module.version` | `str` | Version from manifest |
| `module.description` | `str` | Description from manifest |
| `module.author` | `str` | Author from manifest |
| `module.providers` | `list[str]` | Provider dotted paths |
| `module.manifest` | `dict` | Raw manifest dict |
| `module.has_file(*parts)` | `bool` | Check if file exists inside module |
| `module.import_submodule(path)` | `module` | Import a submodule by relative dotted path |

### `DjangoModuleRegistry`

Extends `ModuleRegistry` with:

| Method | Returns | Description |
|---|---|---|
| `registry.installed_apps()` | `list[str]` | Dotted app paths for `INSTALLED_APPS` |
| `registry.url_patterns()` | `list` | URL patterns from all module `routes.py` files |
| `registry.migration_modules()` | `dict[str, str]` | Dict for `MIGRATION_MODULES` setting |
| `registry.collect_settings()` | `dict` | Merged dict of all module-level settings |

### `detect_framework()`

```python
from pymodules import detect_framework

info = detect_framework(search_path=None)  # defaults to cwd
# info.name          → "django" | "fastapi" | "flask" | "unknown"
# info.preset        → "django" | "fastapi" | "flask" | "default"
# info.confidence    → "high" | "medium" | "low"
# info.reason        → str
# info.all_detected  → list[str]
```

### Exceptions

```python
from pymodules import (
    PyModulesError,          # base exception
    ModuleNotFoundError,     # registry.find("Nonexistent")
    ModuleAlreadyExistsError,# generator.generate("Blog") when it exists + no force
    ModuleDisabledError,     # raised when accessing a disabled module's services
)
```

---

## Feature Status

### ✅ Done — v0.1.0

**Core**
- [x] `ModuleRegistry` — scan, boot, find, enable, disable, iterate
- [x] `Module` — manifest, enable/disable state, import helpers, path helpers
- [x] `module.json` manifest with versioning, providers, publishes
- [x] `ServiceProvider` base class with `register()` and `boot()` hooks
- [x] Boot hooks via `registry.on_boot(fn)` decorator
- [x] Custom folder naming — `modules/`, `plugins/`, `apps/`, `src/features/` — anything
- [x] Typed exceptions (`ModuleNotFoundError`, `ModuleAlreadyExistsError`)

**Framework Detection**
- [x] Three-layer detection: venv import → file fingerprints → dependency scanning
- [x] `DJANGO_SETTINGS_MODULE` env var detection
- [x] Priority resolution when multiple frameworks present (Django > FastAPI > Flask)
- [x] `detect_framework()` public API
- [x] `pymodules detect` CLI command with confidence display

**CLI (`pymodules`)**
- [x] `pymodules init` — project setup with auto-detection
- [x] `pymodules make <n>` — scaffold with preset auto-detection
- [x] `pymodules list` — table view with enable/disable filter
- [x] `pymodules enable` / `pymodules disable`
- [x] `pymodules show` — full module details
- [x] `pymodules delete` — with confirmation prompt
- [x] `pymodules publish` — asset/config publishing with groups
- [x] `pymodules detect` — framework detection report
- [x] `pymodules presets` — list all presets
- [x] `--modules-path` global flag + `PYMODULES_PATH` env var
- [x] `pymodules.toml` project config with walk-up discovery

**Scaffold Presets**
- [x] `plain` preset — `module.json` + `__init__.py`
- [x] `default` preset — framework-agnostic with providers, config, tests
- [x] `django` preset — models, views, apps.py, admin, serializers, migrations
- [x] `django-api` preset — DRF serializer/viewset/router scaffolding
- [x] `fastapi` preset — APIRouter, Pydantic schemas, service layer
- [x] `fastapi-crud` preset — full CRUD APIRouter with update/delete skeletons
- [x] `flask` preset — Blueprint, service layer
- [x] `flask-api` preset — full JSON CRUD Blueprint scaffolding
- [x] `{folder}` token in stubs — providers path always correct regardless of folder name

**Django Integration**
- [x] `DjangoModuleRegistry` — `installed_apps()`, `url_patterns()`, `api_url_patterns()`, `migration_modules()`, `collect_settings()`, `collect_policies()`
- [x] `AppConfig` auto-detection from `apps.py`
- [x] Module-level URL routing with custom `prefix`
- [x] Module-level migrations via `MIGRATION_MODULES`
- [x] Module-level settings merged with `collect_settings()`
- [x] DRF access policy discovery from module `policies.py` / `policies/`
- [x] Dependency-aware startup ordering with warning fallback during Django settings evaluation
- [x] `"pymodules"` as Django app for `manage.py` command discovery
- [x] `manage.py module_make` — with `--preset`, `--force`, smart default to `django`
- [x] `manage.py module_list` — with `--enabled` / `--disabled`
- [x] `manage.py module_enable` / `module_disable`
- [x] `manage.py module_show`
- [x] `manage.py module_delete` — with `--yes` flag
- [x] `manage.py module_publish` — with `--group`, `--force`
- [x] `manage.py module_make_model` — lightweight per-file model scaffold
- [x] `manage.py module_make_serializer` — DRF serializer scaffolding
- [x] `manage.py module_make_viewset` — DRF ViewSet scaffolding
- [x] `manage.py module_make_api_urls` — DRF router URL scaffolding
- [x] `manage.py module_make_model_migration` — migration generation scoped to one model
- [x] `manage.py module_make_migration` — module-scoped `makemigrations`
- [x] `manage.py module_migrate` — module-scoped `migrate`

**Dependencies & Boot Order**
- [x] `module.json` `requires` declarations
- [x] Topological boot ordering for enabled modules
- [x] Circular dependency detection
- [x] Missing / disabled dependency errors

**Flask Integration**
- [x] `FlaskModuleRegistry` — auto-registers Blueprints
- [x] App factory pattern via `init_app(app)`
- [x] Multiple blueprints per module via `blueprints` list

**FastAPI Integration**
- [x] `FastAPIModuleRegistry` — auto-includes APIRouters
- [x] App factory pattern via `init_app(app)`
- [x] Multiple routers per module via `routers` list

**Tests**
- [x] Core registry tests (scan, find, enable, disable, iterate, exists)
- [x] Module tests (manifest, import path, enable persistence, has_file)
- [x] Generator tests (scaffold creation, preset selection, force, duplicate detection)
- [x] Detector tests (per-framework, confidence levels, priority, env var, dep scanning)

---

### 🔄 In Progress

- [ ] **`pymodules upgrade` command** — diff existing module against current preset stubs and offer selective updates
- [ ] **Test coverage enforcement** — `pytest-cov` integration with minimum threshold config in `pymodules.toml`
- [ ] **Detector: `setup.py` scanning** — legacy projects that don't use `pyproject.toml` or `requirements.txt`

---

## Roadmap to Industry Standard

The following is what separates a useful personal tool from a package the Python community adopts as a standard.

#### Documentation & Developer Experience
- [ ] **Dedicated documentation site** (MkDocs + Material theme) — full tutorials, how-to guides, API reference, migration guides
- [ ] **Interactive quickstart** — `pymodules init` walks the user through setup with prompts rather than silent file creation
- [ ] **VS Code extension** — syntax highlighting for `module.json`, module tree sidebar, right-click "Create module" in explorer
- [ ] **PyCharm / IntelliJ plugin** — same as above for JetBrains IDEs
- [ ] **Error messages with fix suggestions** — every raised exception includes the exact command or code to resolve it

#### Architecture & Core
- [ ] **Module versioning and constraints** — `requires: [{"name": "Auth", "version": ">=1.2.0"}]`
- [ ] **Async boot support** — `async def register()` / `async def boot()` in service providers for async frameworks (FastAPI, Starlette, Litestar)
- [ ] **Module events / hooks system** — typed inter-module communication without direct imports (`module.emit("user.created", payload)`)
- [ ] **Lazy loading** — modules only fully imported when first accessed, not at boot time
- [ ] **Hot reload** — detect `module.json` changes at runtime and re-enable/disable without restart (development mode)

#### CLI & Tooling
- [ ] **`pymodules upgrade`** — compare existing module files against current preset stubs, show diff, offer selective updates
- [ ] **`pymodules lint`** — validate all `module.json` files, check for broken provider paths, missing `__init__.py`, import errors
- [ ] **`pymodules graph`** — render module dependency graph in the terminal (or export to Mermaid/DOT)
- [ ] **`pymodules test <ModuleName>`** — run tests scoped to a single module
- [ ] **`pymodules stats`** — line counts, test coverage, complexity per module

#### Framework Support
- [ ] **Litestar integration** — routers, dependency injection, middleware
- [ ] **Starlette integration** — Mount-based routing
- [ ] **Celery integration** — auto-discover tasks from enabled modules
- [ ] **SQLAlchemy integration** — auto-collect models and migrations (Alembic)
- [ ] **Django REST Framework** — auto-register routers from module `api.py`
- [x] **Django REST Framework access policies** — auto-discover `AccessPolicy` classes from module `policies.py`
- [ ] **Django Channels** — WebSocket routing from module `consumers.py`

#### Testing
- [ ] **Integration tests** — full Django, FastAPI, Flask app boot tests
- [ ] **Snapshot tests** — assert generated scaffold files match expected output exactly
- [ ] **Matrix CI** — test Python 3.10, 3.11, 3.12, 3.13 × Django 4.x/5.x × FastAPI × Flask
- [ ] **Mutation testing** — `mutmut` to verify test suite quality
- [ ] **100% line coverage** on core (`module.py`, `registry.py`, `generator.py`, `detector.py`)

#### Distribution & Community
- [x] **PyPI release pipeline** — build + `twine check` + GitHub Actions publish workflow
- [x] **GitHub Actions CI/CD** — test matrix plus release publish workflow
- [x] **Changelog** — `CHANGELOG.md` following Keep a Changelog format
- [x] **Contributing guide** — how to add presets, integrations, CLI commands
- [ ] **Custom preset support** — let users define their own presets in `pymodules.toml` pointing to a local stubs directory
- [ ] **Plugin API** — third-party packages can register new presets, CLI commands, and integrations via entry points
- [x] **Security policy** — `SECURITY.md`, responsible disclosure process
- [ ] **Benchmarks** — boot time with N modules, import overhead vs flat structure

#### Production Readiness
- [ ] **`pymodules.lock`** — deterministic module state snapshot (which modules are enabled, at what version) for reproducible deployments
- [ ] **Module health checks** — `registry.health()` verifies all enabled modules can import cleanly without actually booting them
- [ ] **Structured logging** — opt-in verbose boot logging with module name, provider, timing
- [ ] **Type stubs** — `py.typed` marker, complete `__init__.pyi` for IDE autocomplete on all public APIs
- [ ] **Thread safety** — registry operations safe under concurrent access (WSGI multi-thread, Gunicorn workers)

---

## Contributing

Contributions are welcome. Please open an issue first to discuss what you would like to change.

```bash
git clone https://github.com/tomcroot/pymodules
cd pymodules
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
