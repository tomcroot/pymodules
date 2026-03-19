"""
Framework detector — inspects the current Python environment and project
file system to determine which web framework (if any) is installed and
being used.

Detection runs a layered strategy for each framework:

  Layer 1 — importlib.util.find_spec()
      The definitive check. If the package is importable it's installed.

  Layer 2 — project file fingerprints
      Files that only appear in a project of a specific framework
      (manage.py for Django, typical FastAPI/Flask entry-point names).
      Useful when running pymodules from outside the venv.

  Layer 3 — dependency file scanning
      requirements.txt / pyproject.toml / Pipfile / setup.cfg are scanned
      for framework names as a last-resort hint.

Priority order when multiple frameworks are detected:
    Django > FastAPI > Flask
    (Django is the most opinionated and its presence is unambiguous.)

Public API
----------
    from pymodules.detector import detect_framework, FrameworkInfo

    info = detect_framework()
    print(info.name)          # "django" | "fastapi" | "flask" | "unknown"
    print(info.confidence)    # "high" | "medium" | "low"
    print(info.preset)        # matching generator preset name
    print(info.reason)        # human-readable explanation
"""
from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FrameworkInfo:
    name: str           # "django" | "fastapi" | "flask" | "unknown"
    preset: str         # matching generator preset ("django"|"fastapi"|"flask"|"default")
    confidence: str     # "high" | "medium" | "low"
    reason: str         # human-readable explanation
    all_detected: list[str] = field(default_factory=list)  # every framework found


_PRESET_MAP = {
    "django":  "django",
    "fastapi": "fastapi",
    "flask":   "flask",
    "unknown": "default",
}

# ─────────────────────────────────────────────────────────────────────────────
# Per-framework detection rules
# ─────────────────────────────────────────────────────────────────────────────

# import_names:   importlib.util.find_spec() targets
# file_hints:     files whose *existence* strongly implies this framework
# dep_patterns:   regex patterns to search in dependency files
_FRAMEWORK_RULES: dict[str, dict] = {
    "django": {
        "import_names": ["django"],
        "file_hints": [
            "manage.py",
            "wsgi.py",
            "asgi.py",
            "settings.py",
            "*/settings.py",
            "*/settings/*.py",
        ],
        "dep_patterns": [
            r"\bdjango\b",
            r"\bDjango\b",
        ],
    },
    "fastapi": {
        "import_names": ["fastapi"],
        "file_hints": [],           # no canonical filename — rely on import + deps
        "dep_patterns": [
            r"\bfastapi\b",
            r"\bFastAPI\b",
        ],
    },
    "flask": {
        "import_names": ["flask"],
        "file_hints": [
            "app.py",
            "application.py",
            "wsgi.py",
        ],
        "dep_patterns": [
            r"\bflask\b",
            r"\bFlask\b",
        ],
    },
}

# Ordered priority — first match wins when multiple frameworks detected
_PRIORITY = ["django", "fastapi", "flask"]

# Dependency files to scan (relative to search root)
_DEP_FILES = [
    "requirements.txt",
    "requirements-base.txt",
    "requirements/base.txt",
    "requirements/common.txt",
    "Pipfile",
    "setup.cfg",
    "pyproject.toml",
]


# ─────────────────────────────────────────────────────────────────────────────
# Detection helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_importable(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _find_project_root(start: Path) -> Path:
    """
    Walk up from *start* looking for common project root markers.
    Returns the deepest directory containing any marker, or *start* if none.
    """
    markers = {
        "pyproject.toml", "setup.py", "setup.cfg",
        "Pipfile", "manage.py", ".git",
        "requirements.txt",
    }
    for directory in [start, *start.parents]:
        if any((directory / m).exists() for m in markers):
            return directory
    return start


def _file_hints_match(framework: str, root: Path) -> bool:
    hints = _FRAMEWORK_RULES[framework]["file_hints"]
    for hint in hints:
        if "*" in hint:
            if any(root.glob(hint)):
                return True
        else:
            if (root / hint).exists():
                return True
    return False


def _deps_mention(framework: str, root: Path) -> bool:
    patterns = [re.compile(p, re.IGNORECASE) for p in _FRAMEWORK_RULES[framework]["dep_patterns"]]
    for rel in _DEP_FILES:
        dep_file = root / rel
        if dep_file.exists():
            try:
                text = dep_file.read_text(encoding="utf-8", errors="ignore")
                if any(p.search(text) for p in patterns):
                    return True
            except OSError:
                pass
    return False


def _django_settings_configured() -> bool:
    """True if DJANGO_SETTINGS_MODULE is set in the environment."""
    import os
    return bool(os.environ.get("DJANGO_SETTINGS_MODULE"))


# ─────────────────────────────────────────────────────────────────────────────
# Main detection function
# ─────────────────────────────────────────────────────────────────────────────

def detect_framework(search_path: Path | None = None) -> FrameworkInfo:
    """
    Detect which web framework is active in the current environment.

    Parameters
    ----------
    search_path:
        Directory to search for project files. Defaults to cwd.

    Returns
    -------
    FrameworkInfo
        name, preset, confidence, reason, all_detected
    """
    root = _find_project_root((search_path or Path.cwd()).resolve())

    scores: dict[str, dict] = {}   # framework -> {points, reasons}

    for fw in _PRIORITY:
        points = 0
        reasons: list[str] = []

        # Layer 1: importable — highest confidence
        if any(_is_importable(n) for n in _FRAMEWORK_RULES[fw]["import_names"]):
            points += 10
            reasons.append(f"{fw} is installed in the active Python environment")

        # Special: Django settings env var
        if fw == "django" and _django_settings_configured():
            points += 5
            reasons.append("DJANGO_SETTINGS_MODULE is set")

        # Layer 2: file fingerprints
        if _file_hints_match(fw, root):
            points += 3
            reasons.append(f"found {fw}-specific project files in {root}")

        # Layer 3: dependency files
        if _deps_mention(fw, root):
            points += 2
            reasons.append(f"{fw} listed in dependency files")

        if points > 0:
            scores[fw] = {"points": points, "reasons": reasons}

    if not scores:
        return FrameworkInfo(
            name="unknown",
            preset="default",
            confidence="low",
            reason="No recognised framework detected — using generic preset.",
            all_detected=[],
        )

    all_detected = list(scores.keys())

    # Pick winner by priority order (not just highest score) so Django always
    # beats Flask when both are present (e.g. a Django project with flask in deps)
    winner = next((fw for fw in _PRIORITY if fw in scores), all_detected[0])
    winner_data = scores[winner]
    total = winner_data["points"]

    if total >= 10:
        confidence = "high"
    elif total >= 5:
        confidence = "medium"
    else:
        confidence = "low"

    reason = "; ".join(winner_data["reasons"])
    if len(all_detected) > 1:
        others = [f for f in all_detected if f != winner]
        reason += f" (also detected: {', '.join(others)} — using {winner} by priority)"

    return FrameworkInfo(
        name=winner,
        preset=_PRESET_MAP[winner],
        confidence=confidence,
        reason=reason,
        all_detected=all_detected,
    )
