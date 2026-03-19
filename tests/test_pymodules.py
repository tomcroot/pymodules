"""Tests for pymodules core functionality."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Make sure the package is importable from source
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymodules import ModuleRegistry, ModuleGenerator, Module
from pymodules.exceptions import (
    ModuleAlreadyExistsError,
    ModuleDependencyError,
    ModuleNotFoundError,
)


@pytest.fixture()
def modules_dir(tmp_path: Path) -> Path:
    return tmp_path / "modules"


@pytest.fixture()
def registry(modules_dir: Path) -> ModuleRegistry:
    modules_dir.mkdir()
    return ModuleRegistry(modules_path=modules_dir)


@pytest.fixture()
def populated_registry(modules_dir: Path) -> ModuleRegistry:
    """Registry with Blog (enabled) and Shop (disabled) modules."""
    modules_dir.mkdir()
    for name, enabled in [("Blog", True), ("Shop", False)]:
        mod_dir = modules_dir / name
        mod_dir.mkdir()
        (mod_dir / "__init__.py").write_text("")
        (mod_dir / "module.json").write_text(
            json.dumps({"name": name, "version": "1.0.0", "enabled": enabled})
        )
    return ModuleRegistry(modules_path=modules_dir)


# ------------------------------------------------------------------
# Registry tests
# ------------------------------------------------------------------

class TestModuleRegistry:
    def test_empty_registry(self, registry):
        assert registry.count() == 0
        assert registry.all() == []

    def test_scan_finds_modules(self, populated_registry):
        assert populated_registry.count() == 2

    def test_all_enabled(self, populated_registry):
        enabled = populated_registry.all_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "Blog"

    def test_all_disabled(self, populated_registry):
        disabled = populated_registry.all_disabled()
        assert len(disabled) == 1
        assert disabled[0].name == "Shop"

    def test_find_existing(self, populated_registry):
        blog = populated_registry.find("Blog")
        assert blog.name == "Blog"

    def test_find_missing_raises(self, populated_registry):
        with pytest.raises(ModuleNotFoundError):
            populated_registry.find("Nonexistent")

    def test_exists(self, populated_registry):
        assert populated_registry.exists("Blog")
        assert not populated_registry.exists("Missing")

    def test_contains_operator(self, populated_registry):
        assert "Blog" in populated_registry
        assert "Missing" not in populated_registry

    def test_enable_module(self, populated_registry):
        populated_registry.enable("Shop")
        assert populated_registry.find("Shop").is_enabled

    def test_disable_module(self, populated_registry):
        populated_registry.disable("Blog")
        assert not populated_registry.find("Blog").is_enabled

    def test_iter(self, populated_registry):
        names = [m.name for m in populated_registry]
        assert set(names) == {"Blog", "Shop"}

    def test_boot_calls_provider_register_then_boot(self, registry):
        mod_dir = registry.modules_root / "Blog"
        mod_dir.mkdir()
        (mod_dir / "__init__.py").write_text("")
        (mod_dir / "module.json").write_text(
            json.dumps(
                {
                    "name": "Blog",
                    "enabled": True,
                    "providers": ["fakepkg.FakeProvider"],
                }
            )
        )
        registry.scan()

        calls: list[tuple[str, str]] = []

        class FakeProvider:
            def __init__(self, module, app=None):
                self.module = module

            def register(self):
                calls.append(("register", self.module.name))

            def boot(self):
                calls.append(("boot", self.module.name))

        with patch(
            "pymodules.registry.importlib.import_module",
            return_value=SimpleNamespace(FakeProvider=FakeProvider),
        ):
            registry.boot()

        assert calls == [("register", "Blog"), ("boot", "Blog")]

    def test_all_enabled_ordered_respects_requires(self, registry):
        for name, requires in [
            ("Core", []),
            ("Sales", ["Core"]),
            ("Inventory", ["Core"]),
        ]:
            mod_dir = registry.modules_root / name
            mod_dir.mkdir()
            (mod_dir / "__init__.py").write_text("")
            (mod_dir / "module.json").write_text(
                json.dumps({"name": name, "enabled": True, "requires": requires})
            )

        registry.scan()
        ordered = [m.name for m in registry.all_enabled_ordered()]
        assert ordered[0] == "Core"
        assert set(ordered[1:]) == {"Inventory", "Sales"}

    def test_all_enabled_ordered_raises_on_missing_dependency(self, registry):
        mod_dir = registry.modules_root / "Sales"
        mod_dir.mkdir()
        (mod_dir / "__init__.py").write_text("")
        (mod_dir / "module.json").write_text(
            json.dumps(
                {
                    "name": "Sales",
                    "enabled": True,
                    "requires": ["Core"],
                }
            )
        )
        registry.scan()

        with pytest.raises(ModuleDependencyError):
            registry.all_enabled_ordered()

    def test_all_enabled_ordered_raises_on_cycle(self, registry):
        for name, requires in [
            ("A", ["B"]),
            ("B", ["A"]),
        ]:
            mod_dir = registry.modules_root / name
            mod_dir.mkdir()
            (mod_dir / "__init__.py").write_text("")
            (mod_dir / "module.json").write_text(
                json.dumps({"name": name, "enabled": True, "requires": requires})
            )
        registry.scan()

        with pytest.raises(ModuleDependencyError):
            registry.all_enabled_ordered()


# ------------------------------------------------------------------
# Module tests
# ------------------------------------------------------------------

class TestModule:
    def test_manifest_loaded(self, populated_registry):
        blog = populated_registry.find("Blog")
        assert blog.version == "1.0.0"

    def test_import_path(self, populated_registry):
        blog = populated_registry.find("Blog")
        assert blog.import_path.endswith("Blog")

    def test_enable_persists(self, populated_registry):
        shop = populated_registry.find("Shop")
        assert not shop.is_enabled
        shop.enable()
        # Re-read manifest from disk
        shop._manifest = None
        assert shop.is_enabled

    def test_has_file(self, populated_registry):
        blog = populated_registry.find("Blog")
        assert blog.has_file("module.json")
        assert not blog.has_file("nonexistent.py")


# ------------------------------------------------------------------
# Generator tests
# ------------------------------------------------------------------

class TestModuleGenerator:
    def test_generate_creates_files(self, registry, modules_dir):
        gen = ModuleGenerator(registry)
        path = gen.generate("Billing")
        assert path.exists()
        assert (path / "module.json").exists()
        assert (path / "__init__.py").exists()
        assert (path / "providers.py").exists()

    def test_generate_registers_in_registry(self, registry):
        gen = ModuleGenerator(registry)
        gen.generate("Billing")
        assert registry.exists("Billing")

    def test_generate_plain(self, registry):
        gen = ModuleGenerator(registry, preset="plain")
        path = gen.generate("Slim")
        assert (path / "module.json").exists()
        assert not (path / "providers.py").exists()

    def test_generate_django_routes_import_existing_views(self, registry):
        gen = ModuleGenerator(registry, preset="django")
        path = gen.generate("Blog")
        routes = (path / "routes.py").read_text()
        assert "from .views.blog_views import index, detail" in routes
        assert "path(\"\", index, name=\"index\")" in routes

    def test_generate_duplicate_raises(self, registry):
        gen = ModuleGenerator(registry)
        gen.generate("Dupe")
        with pytest.raises(ModuleAlreadyExistsError):
            gen.generate("Dupe")

    def test_generate_force_overwrites(self, registry):
        gen = ModuleGenerator(registry)
        gen.generate("Overwrite")
        gen_force = ModuleGenerator(registry, force=True)
        path = gen_force.generate("Overwrite")
        assert path.exists()

    def test_manifest_content(self, registry):
        gen = ModuleGenerator(registry)
        path = gen.generate("Invoice")
        manifest = json.loads((path / "module.json").read_text())
        assert manifest["name"] == "Invoice"
        assert manifest["enabled"] is True
        assert "providers" in manifest

    def test_module_config_exists_in_generator(self, registry):
        """Verify generator includes config/config.py in generated modules."""
        gen = ModuleGenerator(registry, preset="django")
        path = gen.generate("Config")
        assert (path / "config" / "config.py").exists()
        config_content = (path / "config" / "config.py").read_text()
        assert "HTTP_TIMEOUT" in config_content or len(config_content) > 0
