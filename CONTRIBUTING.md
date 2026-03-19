# Contributing to pymodules

Thank you for your interest in contributing! This document covers how to set up your development environment, run tests, and submit changes.

---

## Before You Start

Please **open an issue first** to discuss what you would like to change. This avoids wasted effort if the direction doesn't align with the project's goals.

---

## Development Setup

**Requirements:** Python 3.10+, Git

```bash
# 1. Fork and clone
git clone https://github.com/tomcroot/pymodules
cd pymodules

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install in editable mode with all dev dependencies
pip install -e ".[dev]"

# 4. Verify everything works
pytest
```

---

## Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=pymodules --cov-report=term-missing

# Single test file
pytest tests/test_pymodules.py -v
```

The test suite must pass on all supported Python versions (3.10–3.13) before a PR is merged. CI runs automatically on every push and pull request.

---

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/<short-description>` | `feat/module-groups` |
| Bug fix | `fix/<short-description>` | `fix/django-routes-import` |
| Documentation | `docs/<short-description>` | `docs/fastapi-guide` |
| Chore / tooling | `chore/<short-description>` | `chore/update-ci` |

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add module_make_view command
fix: correct provider boot order when dependency missing
docs: update Django integration example
chore: bump pytest to 8.0
```

---

## Pull Request Requirements

- [ ] Tests pass (`pytest`)
- [ ] New behaviour is covered by tests
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] No `yourname` / placeholder text in any file
- [ ] PR description explains what changed and why

---

## Project Structure

```
pymodules/
├── __init__.py           — public API
├── module.py             — Module model
├── registry.py           — ModuleRegistry (boot orchestration)
├── generator.py          — scaffold presets
├── provider.py           — ServiceProvider base
├── detector.py           — framework auto-detection
├── exceptions.py         — custom exception hierarchy
├── commands/             — pymodules CLI (Click)
├── integrations/         — Django / Flask / FastAPI adapters
└── management/           — Django manage.py commands
    └── commands/
tests/
└── test_pymodules.py
```

---

## Reporting Bugs

Open a GitHub issue and include:

- Python version (`python --version`)
- pymodules version
- Minimal reproduction case
- Full traceback

---

## License

By contributing you agree that your contributions will be licensed under the [MIT License](LICENSE).
