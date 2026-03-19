"""Custom exceptions for pymodules."""


class PyModulesError(Exception):
    """Base exception for all pymodules errors."""


class ModuleNotFoundError(PyModulesError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Module {name!r} could not be found.")


class ModuleAlreadyExistsError(PyModulesError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Module {name!r} already exists.")


class ModuleDisabledError(PyModulesError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Module {name!r} is disabled.")


class ModuleDependencyError(PyModulesError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
