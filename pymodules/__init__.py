"""
pymodules — Laravel-modules inspired modular architecture for Python.

Quick start::

    from pymodules import ModuleRegistry

    registry = ModuleRegistry(modules_path="modules")
    registry.boot()

Django::

    from pymodules.integrations.django import DjangoModuleRegistry
    registry = DjangoModuleRegistry(modules_path=BASE_DIR / "modules")
    INSTALLED_APPS += registry.installed_apps()

Flask::

    from pymodules.integrations.flask import FlaskModuleRegistry
    registry = FlaskModuleRegistry(modules_path="modules", app=flask_app)

FastAPI::

    from pymodules.integrations.fastapi import FastAPIModuleRegistry
    registry = FastAPIModuleRegistry(modules_path="modules", app=fastapi_app)
"""

from .detector import FrameworkInfo, detect_framework
from .exceptions import (
    ModuleAlreadyExistsError,
    ModuleDependencyError,
    ModuleDisabledError,
    ModuleNotFoundError,
    PyModulesError,
)
from .generator import ModuleGenerator
from .module import Module
from .provider import ServiceProvider
from .registry import ModuleRegistry

__all__ = [
    "FrameworkInfo",
    "Module",
    "ModuleAlreadyExistsError",
    "ModuleDependencyError",
    "ModuleDisabledError",
    "ModuleGenerator",
    "ModuleNotFoundError",
    "ModuleRegistry",
    "PyModulesError",
    "ServiceProvider",
    "detect_framework",
]

__version__ = "0.1.0"
