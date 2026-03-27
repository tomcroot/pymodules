# pymodules v2 Specification

Status: Implemented foundation in v0.2.0; planned items remain for future versions
Audience: Maintainers and contributors
Scope: Core runtime, discovery, lifecycle, extension registry, and framework adapters

## 1) Goals

pymodules v2 keeps the package framework-agnostic while evolving from a module loader + provider runner into a typed extension runtime with explicit lifecycle stages.

Primary goals:
- Keep generic kernel behavior and avoid ERP-specific semantics.
- Introduce explicit module metadata and lifecycle contracts.
- Add extension-point registration as first-class runtime API.
- Preserve existing v1 behavior through a compatibility layer.
- Keep Django/Flask/FastAPI as adapters over the same core runtime.

Non-goals:
- Tenant model, role model, permission enforcement, workflow engines.
- Domain ownership of menu/widget/permission semantics.

## 2) Design Principles

- Backward-compatible by default for one major cycle.
- Declarative registration, operational boot.
- Deterministic ordering and deterministic discovery precedence.
- Framework adapters consume extension buckets, not internals.
- Strict runtime validation, startup-tolerant adapter behavior where required.

## 3) Versioned Contracts

## 3.1 Module metadata

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ModuleMeta:
    name: str
    key: str
    version: str
    description: str = ""
    dependencies: tuple[str, ...] = ()
    optional_dependencies: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    enabled_by_default: bool = True
```

Rules:
- key is globally unique across all discovery backends.
- name is human-readable; key is stable identifier.
- dependencies must resolve to enabled modules during resolve stage.
- optional_dependencies are ignored if missing/disabled.

## 3.2 Runtime module contract

```python
from typing import Any, Iterable, Protocol

class RegistryProtocol(Protocol):
    def add(self, extension_point: str, value: Any, *, module: str) -> None: ...
    def add_many(self, extension_point: str, values: Iterable[Any], *, module: str) -> None: ...

class BaseModule:
    meta: ModuleMeta

    def register(self, registry: RegistryProtocol) -> None:
        """Declare extensions only. No side effects."""

    def boot(self, app: Any | None = None) -> None:
        """Runtime initialization after global registration."""

    def shutdown(self, app: Any | None = None) -> None:
        """Optional cleanup."""

    def healthcheck(self) -> dict[str, Any]:
        return {"ok": True}
```

Note:
- v2 enforces separation of declaration and initialization for new-style modules.
- v1 ServiceProvider modules remain supported through compatibility shims (see section 8).

## 3.3 Extension registry

```python
class ExtensionRegistry:
    def add(self, extension_point: str, value: Any, *, module: str) -> None: ...
    def add_many(self, extension_point: str, values: Iterable[Any], *, module: str) -> None: ...
    def get(self, extension_point: str) -> list[Any]: ...
    def get_by_module(self, extension_point: str, module: str) -> list[Any]: ...
    def map(self, extension_point: str) -> dict[str, list[Any]]: ...
```

Core extension points reserved by pymodules:
- routes
- api_routes
- settings
- commands
- providers
- policies
- events.listeners
- signals
- migrations
- templates
- assets

All other point names are allowed but treated as opaque data buckets by core.

## 3.4 ModuleRegistry v2 API

Current implementation (in v0.2.0):

```python
class ModuleRegistry:
    # lifecycle
    def discover(self) -> None: ...
    def resolve(self) -> list[str]: ...
    def instantiate(self) -> None: ...
    def register_all(self) -> None: ...
    def boot_all(self, app: Any | None = None) -> None: ...
    def shutdown_all(self, app: Any | None = None) -> None: ...

    # extensions
    def extensions(self, point: str) -> list[Any]: ...
    def extension_map(self, point: str) -> dict[str, list[Any]]: ...
    def add(self, point: str, value: Any, *, module: str) -> None: ...
    def add_many(self, point: str, values: Iterable[Any], *, module: str) -> None: ...
```

Planned APIs (not implemented yet):

```python
class ModuleRegistry:
    # introspection
    def modules(self) -> list[BaseModule]: ...
    def module(self, key: str) -> BaseModule: ...

    # events
    def on(self, event: str, listener: Any, *, module: str) -> None: ...
    def emit(self, event: str, payload: Any | None = None) -> None: ...
```

Compatibility aliases for v1 users:
- scan() -> discover()
- boot() -> register_all(); boot_all()
- all()/find()/exists() preserved for v2 transitional period

## 4) Loader Lifecycle

Stages:
1. discover
2. resolve
3. instantiate
4. register
5. boot
6. serve (adapter consumes extension buckets)
7. shutdown

Invariants:
- register never performs runtime side effects.
- boot runs after every module has completed register.
- shutdown runs reverse dependency order.

## 5) Discovery Backends

Supported backends:
- Filesystem modules directory.
- Python entry points.

Entry point group:

```toml
[project.entry-points."pymodules.modules"]
finance = "myapp.modules.finance:FinanceModule"
hr = "myapp.modules.hr:HRModule"
```

Both `module:attr` (entry-point style) and `module.attr` class paths are accepted for `module_class` loading.

Precedence and collisions:
- Explicitly configured modules (if provided) win.
- Filesystem modules are evaluated next.
- Entry points are evaluated last.
- Duplicate key across any backend raises a resolve error with source details.

Reference runtime knobs:
- `include_entry_points`: opt-in entry-point discovery (default `False`).
- `discovery_order`: source precedence tuple (default `("filesystem", "entry_points")`).
- `duplicate_policy`: duplicate handling mode (`"error"`, `"prefer-first"`, `"prefer-last"`; default `"error"`).

## 6) Adapter Model

Framework integrations become adapters over ModuleRegistry + ExtensionRegistry.

## 6.1 Django adapter

```python
class DjangoModuleAdapter:
    def installed_apps(self) -> list[str]: ...
    def urlpatterns(self) -> list[Any]: ...
    def api_urlpatterns(self, prefix: str = "api") -> list[Any]: ...
    def migration_modules(self) -> dict[str, str]: ...
    def settings_overrides(self) -> dict[str, Any]: ...
    def management_commands(self) -> list[Any]: ...
```

Startup tolerance:
- During settings import, adapter may warn and degrade to enabled-order if dependency resolution fails.
- During runtime boot, strict resolve is enforced.

## 7) Policy Handling

Core behavior:
- Core only stores policy registrations as extension values.
- Core does not execute policy engine semantics.

Example:

```python
registry.add("policies", InvoiceAccessPolicy, module="finance")
```

Adapter behavior:
- Django adapter may expose helper accessors for DRF integration.
- Non-DRF applications can consume same policies extension for alternate engines.

## 8) Backward Compatibility and Deprecation

v2 compatibility requirements:
- Existing module.json discovery remains valid.
- Existing providers list in module.json remains valid.
- ServiceProvider subclasses continue to run during transition.

Compatibility strategy:
- Adapter wraps v1 ServiceProvider register/boot into v2 lifecycle.
- register side effects are allowed only in compatibility mode.
- New BaseModule contract is default for new scaffolds.

Deprecation policy:
- v2.x: compatibility mode on by default; warnings for runtime side effects in register.
- v3.0: remove compatibility mode by default; opt-in legacy plugin only.

## 9) Migration Plan

Phase 1 (foundation)
- Add ModuleMeta, BaseModule, and ExtensionRegistry.
- Keep module.json as discovery transport format.
- Add compatibility adapters for v1 providers.

Phase 2 (runtime)
- Split registry into discover/resolve/instantiate/register/boot/shutdown.
- Add entry-point discovery.
- Add event bus.

Phase 3 (frameworks)
- Refactor Django integration to adapter model.
- Move route/settings/policy collection to extension consumption where possible.
- Deprecate import scanning where explicit registration exists.

## 10) Package Layout (target)

```text
pymodules/
  core/
    contracts.py        # ModuleMeta, BaseModule, protocols
    extensions.py       # ExtensionRegistry
    lifecycle.py        # stage orchestration
    events.py           # event bus
  discovery/
    filesystem.py
    entrypoints.py
  adapters/
    django.py
    flask.py
    fastapi.py
  compatibility/
    service_provider.py # v1 bridge
  registry.py           # facade API
```

## 11) Error Model

Errors should be explicit and stage-bound:
- DiscoveryError
- ResolveError
- ModuleCollisionError
- ContractValidationError
- RegisterError
- BootError

Current ModuleDependencyError remains supported as alias during transition.

## 12) Test Strategy

Unit tests:
- dependency graph ordering and cycles
- duplicate module key collisions across backends
- extension registry add/get/map semantics
- event bus listener registration and dispatch ordering
- shutdown reverse-order behavior

Compatibility tests:
- v1 provider register then boot ordering preserved
- module.json enable/disable behavior preserved
- Django startup warning fallback preserved

Adapter tests:
- Django installed apps/url/migration/settings collection from registered extensions
- policy registrations exposed without hard dependency on DRF unless requested

Integration tests:
- mixed discovery (filesystem + entry points)
- mixed module types (BaseModule + ServiceProvider legacy)
- repeated lifecycle calls are idempotent where documented

## 13) Acceptance Criteria (v2.0)

- New modules can be authored solely with BaseModule + ModuleMeta.
- Existing v1 modules work without code changes.
- Registry exposes extension data for framework adapters.
- Discovery supports both filesystem and entry points with deterministic behavior.
- Public docs include migration examples from v1 to v2.

## 14) Open Decisions

- Whether strict resolve failure should ever block Django settings import.
- Whether commands/policies should be reserved extension point names or adapter-owned conventions.
- Exact deprecation timeline for ServiceProvider runtime side effects.
