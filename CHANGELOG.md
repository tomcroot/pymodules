# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] - 2026-03-19

### Added

- Framework-agnostic `ModuleRegistry`, `Module`, and `ServiceProvider` core
- Auto-detection of Django, FastAPI, Flask from your project environment
- `pymodules` CLI: `init`, `make`, `list`, `enable`, `disable`, `show`, `delete`, `publish`, `detect`, `presets`
- Django `manage.py` integration commands:
  - `module_make` — scaffold a new module
  - `module_list` — list all modules and their status
  - `module_enable` / `module_disable` — toggle modules at runtime
  - `module_show` — inspect a module's manifest
  - `module_delete` — remove a module from disk
  - `module_publish` — publish module assets to the host app
  - `module_make_model` — create a lightweight, non-bloated model file
  - `module_make_model_migration` — create a migration targeting a specific model
  - `module_make_migration` — run `makemigrations` scoped to one module
  - `module_migrate` — run `migrate` scoped to one module (or all)
- Five scaffold presets: `plain`, `default`, `django`, `fastapi`, `flask`
- Per-project configuration via `pymodules.toml`
- `module.json` manifest with versioning, enable/disable, provider registration, and dependency declarations
- Service Provider pattern with two-phase `register` → `boot` lifecycle
- Module dependency declarations (`requires`) with topological boot ordering
- Circular and missing dependency detection with actionable error messages
- Module-level settings merged into Django `settings` via `collect_settings()`
- Module-level URL routing for Django, Flask, and FastAPI
- Module-level Django migrations with `MIGRATION_MODULES` auto-configuration
- Asset publishing system
- Python 3.10, 3.11, 3.12, 3.13 support

[Unreleased]: https://github.com/tomcroot/pymodules/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tomcroot/pymodules/releases/tag/v0.1.0
