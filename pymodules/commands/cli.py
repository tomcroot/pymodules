"""
CLI for pymodules.

Framework detection is automatic — pymodules inspects your environment and
project files to determine Django / FastAPI / Flask and picks the right
scaffold preset automatically. You can always override with --preset.

  pymodules init               # auto-detects framework, writes pymodules.toml
  pymodules make Blog          # auto-detects framework, creates correct scaffold
  pymodules make Blog --preset flask   # explicit override
  pymodules detect             # show what framework was detected and why

Config file (pymodules.toml) priority:
  1. --modules-path / --preset CLI flags  (highest)
  2. pymodules.toml in project root
  3. Auto-detected framework              (lowest / fallback)
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import click

from ..registry import ModuleRegistry
from ..generator import ModuleGenerator, PRESETS
from ..detector import detect_framework, FrameworkInfo
from ..exceptions import ModuleNotFoundError, ModuleAlreadyExistsError

# ─────────────────────────────────────────────────────────────────────────────
# Config file helpers
# ─────────────────────────────────────────────────────────────────────────────

CONFIG_FILENAME = "pymodules.toml"

_CONFIG_TEMPLATE = """\
# pymodules.toml — project configuration for pymodules
# Commit this file so your whole team shares the same settings.

[pymodules]
# Where your modules/plugins live. Name this anything you like:
#   "modules", "plugins", "apps", "src/components", etc.
modules_path = "{modules_path}"

# Default scaffold preset used by `pymodules make`.
# Auto-detected from your environment — change if needed.
# Choices: default | plain | django | fastapi | flask
default_preset = "{default_preset}"

# Framework that was detected at init time (informational only).
detected_framework = "{detected_framework}"
"""


def _load_config(start: Path | None = None) -> dict:
    """Walk up from *start* (default: cwd) looking for pymodules.toml."""
    search = (start or Path.cwd()).resolve()
    for directory in [search, *search.parents]:
        cfg = directory / CONFIG_FILENAME
        if cfg.exists():
            with cfg.open("rb") as f:
                return tomllib.load(f).get("pymodules", {})
    return {}


def _resolve_modules_path(cli_value: str) -> str:
    """
    Resolution order:
      1. --modules-path CLI flag
      2. pymodules.toml modules_path
      3. "modules" (hardcoded fallback)
    """
    if cli_value != "__unset__":
        return cli_value
    return _load_config().get("modules_path", "modules")


def _resolve_preset(cli_value: str | None) -> tuple[str, str]:
    """
    Resolve the preset to use and return (preset, source) where source
    explains where the preset came from (for user feedback).

    Resolution order:
      1. --preset CLI flag
      2. pymodules.toml default_preset
      3. Auto-detected framework
      4. "default" (hardcoded fallback)
    """
    if cli_value:
        return cli_value, "explicit --preset flag"

    cfg = _load_config()
    if "default_preset" in cfg:
        return cfg["default_preset"], f"{CONFIG_FILENAME}"

    info = detect_framework()
    if info.name != "unknown":
        return info.preset, f"auto-detected {info.name} ({info.confidence} confidence)"

    return "default", "no framework detected — using generic preset"


def _get_registry(modules_path: str) -> ModuleRegistry:
    return ModuleRegistry(modules_path=modules_path)


# ─────────────────────────────────────────────────────────────────────────────
# Root group
# ─────────────────────────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--modules-path",
    default="__unset__",
    envvar="PYMODULES_PATH",
    help="Override the modules directory path.",
)
@click.pass_context
def cli(ctx: click.Context, modules_path: str) -> None:
    """pymodules — modular Python application management.

    Framework detection is automatic. Run `pymodules detect` to see
    what was found, or `pymodules init` to set up a new project.
    """
    ctx.ensure_object(dict)
    ctx.obj["modules_path_raw"] = modules_path


# ─────────────────────────────────────────────────────────────────────────────
# detect — show framework detection result
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("detect")
@click.option("--path", default=None, help="Project root to scan (default: cwd).")
def detect_command(path: str | None) -> None:
    """Show which framework pymodules detected in this project.

    \b
    Examples:
      pymodules detect
      pymodules detect --path /path/to/project
    """
    search = Path(path) if path else None
    info = detect_framework(search)

    confidence_color = {"high": "green", "medium": "yellow", "low": "red"}

    click.echo()
    click.echo(f"  Framework  : {click.style(info.name, bold=True)}")
    click.echo(f"  Preset     : {info.preset}")
    click.echo(
        f"  Confidence : "
        + click.style(info.confidence, fg=confidence_color.get(info.confidence, "white"))
    )
    click.echo(f"  Reason     : {info.reason}")
    if len(info.all_detected) > 1:
        click.echo(f"  Also found : {', '.join(f for f in info.all_detected if f != info.name)}")
    click.echo()

    if info.confidence == "low":
        click.echo(
            click.style(
                "  Tip: install your framework in this virtualenv for higher confidence,\n"
                "  or run `pymodules init --preset <name>` to set it explicitly.",
                fg="yellow",
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# init — create pymodules.toml
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("init")
@click.option("--path", default=None, help="modules_path (default: auto or 'modules').")
@click.option(
    "--preset", default=None,
    type=click.Choice(list(PRESETS)),
    help="Default preset (default: auto-detected).",
)
@click.option("--force", is_flag=True, help="Overwrite existing pymodules.toml.")
def init_project(path: str | None, preset: str | None, force: bool) -> None:
    """Initialise pymodules in the current project.

    Auto-detects your framework and writes a pymodules.toml config file.
    You can always override the detection with --preset.

    \b
    Examples:
      pymodules init                          # fully automatic
      pymodules init --path plugins           # custom folder name
      pymodules init --preset fastapi         # force a specific preset
      pymodules init --path apps --preset django
    """
    cfg_path = Path.cwd() / CONFIG_FILENAME

    if cfg_path.exists() and not force:
        click.echo(
            click.style(
                f"{CONFIG_FILENAME} already exists. Use --force to overwrite.",
                fg="yellow",
            )
        )
        return

    # ── Auto-detect ──────────────────────────────────────────────────────────
    info = detect_framework()

    resolved_preset = preset or info.preset
    resolved_path   = path or "modules"

    # Write config
    content = _CONFIG_TEMPLATE.format(
        modules_path=resolved_path,
        default_preset=resolved_preset,
        detected_framework=info.name,
    )
    cfg_path.write_text(content)

    # Create the modules directory + __init__.py
    mod_dir = Path.cwd() / resolved_path
    mod_dir.mkdir(parents=True, exist_ok=True)
    init_file = mod_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(f'"""Root package for {resolved_path}."""\n')

    # ── Output ───────────────────────────────────────────────────────────────
    click.echo()
    click.echo(click.style("  pymodules initialised!", fg="green", bold=True))
    click.echo()
    click.echo(f"  Config file      : {CONFIG_FILENAME}")
    click.echo(f"  Modules folder   : {resolved_path}/")
    click.echo(f"  Default preset   : {resolved_preset}")

    if info.name != "unknown":
        confidence_color = {"high": "green", "medium": "yellow", "low": "red"}
        click.echo(
            f"  Detected         : "
            + click.style(info.name, fg=confidence_color.get(info.confidence, "white"))
            + f" ({info.confidence} confidence)"
        )
    else:
        click.echo(
            click.style(
                "\n  No framework detected. Using generic preset.\n"
                "  Install Django/FastAPI/Flask in your venv for auto-detection,\n"
                "  or edit pymodules.toml to set default_preset manually.",
                fg="yellow",
            )
        )

    click.echo()
    click.echo("  Next step:")
    click.echo(f"    pymodules make <ModuleName>")
    click.echo()

    if preset and preset != info.preset and info.name != "unknown":
        click.echo(
            click.style(
                f"  Note: detected {info.name} but you chose --preset {preset}. "
                "That's fine — your choice takes precedence.",
                fg="cyan",
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# make
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("make")
@click.argument("name")
@click.option(
    "--preset", "-p",
    type=click.Choice(list(PRESETS)),
    default=None,
    help="Scaffold preset. Overrides auto-detection and pymodules.toml.",
)
@click.option("--force", is_flag=True, help="Overwrite existing module.")
@click.pass_context
def make_module(ctx: click.Context, name: str, preset: str | None, force: bool) -> None:
    """Create a new module scaffold.

    The preset is chosen automatically:
      1. --preset flag (you override)
      2. pymodules.toml default_preset
      3. Auto-detected framework (Django/FastAPI/Flask)
      4. Generic "default" preset

    \b
    Preset contents:
      default   providers.py, config/, tests/
      django    + models, views, apps.py, admin, serializers, migrations
      fastapi   + APIRouter, Pydantic schemas, service layer
      flask     + Blueprint, service layer
      plain     module.json + __init__.py only

    \b
    Examples:
      pymodules make Blog                    # auto-detected preset
      pymodules make Auth --preset django    # explicit
      pymodules make Cart --preset fastapi
    """
    modules_path = _resolve_modules_path(ctx.obj["modules_path_raw"])
    resolved_preset, preset_source = _resolve_preset(preset)

    registry  = _get_registry(modules_path)
    generator = ModuleGenerator(registry, preset=resolved_preset, force=force)

    try:
        created_path = generator.generate(name)
    except ModuleAlreadyExistsError as e:
        click.echo(click.style(str(e) + "  Use --force to overwrite.", fg="red"), err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)

    click.echo()
    click.echo(click.style(f"  ✓ Module {name!r} created", fg="green", bold=True))
    click.echo(f"    Path   : {created_path}")
    click.echo(f"    Preset : {resolved_preset}  (from {preset_source})")
    click.echo()
    _print_tree(created_path)
    click.echo()


def _print_tree(base: Path, indent: str = "    ") -> None:
    for item in sorted(base.rglob("*")):
        if item.name == ".gitkeep":
            continue
        rel   = item.relative_to(base)
        depth = len(rel.parts)
        pad   = indent + "  " * (depth - 1)
        icon  = "  " if item.is_dir() else "  "
        click.echo(f"{pad}{icon}{item.name}")


# ─────────────────────────────────────────────────────────────────────────────
# list
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("list")
@click.option("--enabled-only",  is_flag=True)
@click.option("--disabled-only", is_flag=True)
@click.pass_context
def list_modules(ctx: click.Context, enabled_only: bool, disabled_only: bool) -> None:
    """List all modules."""
    modules_path = _resolve_modules_path(ctx.obj["modules_path_raw"])
    registry = _get_registry(modules_path)
    modules  = registry.all()

    if enabled_only:
        modules = [m for m in modules if m.is_enabled]
    elif disabled_only:
        modules = [m for m in modules if not m.is_enabled]

    click.echo(f"\n  Modules path: {modules_path}/  ({len(modules)} found)\n")

    if not modules:
        click.echo("  No modules found. Run `pymodules make <Name>` to create one.\n")
        return

    click.echo(f"  {'Name':<25} {'Status':<12} {'Version':<10} Description")
    click.echo("  " + "─" * 66)
    for m in modules:
        status = click.style("enabled", fg="green") if m.is_enabled else click.style("disabled", fg="red")
        click.echo(f"  {m.name:<25} {status:<20} {m.version:<10} {m.description}")
    click.echo()


# ─────────────────────────────────────────────────────────────────────────────
# enable / disable
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("enable")
@click.argument("name")
@click.pass_context
def enable_module(ctx: click.Context, name: str) -> None:
    """Enable a module."""
    modules_path = _resolve_modules_path(ctx.obj["modules_path_raw"])
    try:
        _get_registry(modules_path).enable(name)
        click.echo(click.style(f"  ✓ Module {name!r} enabled.", fg="green"))
    except ModuleNotFoundError as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)


@cli.command("disable")
@click.argument("name")
@click.pass_context
def disable_module(ctx: click.Context, name: str) -> None:
    """Disable a module."""
    modules_path = _resolve_modules_path(ctx.obj["modules_path_raw"])
    try:
        _get_registry(modules_path).disable(name)
        click.echo(click.style(f"  ✓ Module {name!r} disabled.", fg="yellow"))
    except ModuleNotFoundError as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# delete
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("delete")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
@click.pass_context
def delete_module(ctx: click.Context, name: str, yes: bool) -> None:
    """Delete a module from disk."""
    import shutil

    modules_path = _resolve_modules_path(ctx.obj["modules_path_raw"])
    registry = _get_registry(modules_path)
    try:
        module = registry.find(name)
    except ModuleNotFoundError as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)

    if not yes:
        click.confirm(f"  Delete module {name!r} at {module.path}?", abort=True)

    shutil.rmtree(module.path)
    click.echo(click.style(f"  ✓ Module {name!r} deleted.", fg="green"))


# ─────────────────────────────────────────────────────────────────────────────
# show
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("show")
@click.argument("name")
@click.pass_context
def show_module(ctx: click.Context, name: str) -> None:
    """Show details for a single module."""
    modules_path = _resolve_modules_path(ctx.obj["modules_path_raw"])
    try:
        m = _get_registry(modules_path).find(name)
    except ModuleNotFoundError as e:
        click.echo(click.style(str(e), fg="red"), err=True)
        sys.exit(1)

    click.echo()
    click.echo(f"  Name        : {m.name}")
    click.echo(f"  Status      : {'enabled' if m.is_enabled else 'disabled'}")
    click.echo(f"  Version     : {m.version}")
    click.echo(f"  Description : {m.description}")
    click.echo(f"  Author      : {m.author}")
    click.echo(f"  Path        : {m.path}")
    click.echo(f"  Import path : {m.import_path}")
    if m.providers:
        click.echo(f"  Providers   : {', '.join(m.providers)}")
    click.echo()


# ─────────────────────────────────────────────────────────────────────────────
# publish
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("publish")
@click.argument("name", required=False)
@click.option("--group", default="default", help="Publish group.")
@click.option("--force", is_flag=True)
@click.pass_context
def publish_module(ctx: click.Context, name: str | None, group: str, force: bool) -> None:
    """Publish module assets / config files to the host application."""
    import shutil

    modules_path = _resolve_modules_path(ctx.obj["modules_path_raw"])
    registry = _get_registry(modules_path)
    targets  = [registry.find(name)] if name else registry.all_enabled()

    for m in targets:
        publishes = m.manifest.get("publishes", {}).get(group, {})
        for src, dest in publishes.items():
            src_path  = m.path / src
            dest_path = Path(dest)
            if dest_path.exists() and not force:
                click.echo(f"  skip {dest}  (use --force to overwrite)")
                continue
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            click.echo(click.style(f"  ✓ {src} → {dest}", fg="green"))


# ─────────────────────────────────────────────────────────────────────────────
# presets
# ─────────────────────────────────────────────────────────────────────────────

@cli.command("presets")
def list_presets() -> None:
    """List all available scaffold presets."""
    rows = {
        "plain":        "module.json + __init__.py only",
        "default":      "Framework-agnostic: providers, config, tests",
        "django":       "Django: models, HTML views, admin, migrations",
        "django-api":   "Django REST: DRF ViewSet, Serializer, DefaultRouter, api/urls.py",
        "fastapi":      "FastAPI: APIRouter, Pydantic schemas, service (3 endpoints)",
        "fastapi-crud": "FastAPI: full CRUD — list/get/create/update/delete (5 endpoints)",
        "flask":        "Flask: Blueprint, service layer",
        "flask-api":    "Flask REST: Blueprint full CRUD JSON API (5 endpoints)",
    }
    click.echo()
    click.echo(f"  {'Preset':<16}  Description")
    click.echo("  " + "─" * 70)
    for name, desc in rows.items():
        click.echo(f"  {name:<16}  {desc}")
    click.echo()
