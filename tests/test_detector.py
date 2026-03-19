"""Tests for the framework detector."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymodules.detector import detect_framework, FrameworkInfo


class TestDetectFramework:

    def test_returns_framework_info(self, tmp_path):
        info = detect_framework(tmp_path)
        assert isinstance(info, FrameworkInfo)
        assert info.name in ("django", "fastapi", "flask", "unknown")
        assert info.preset in ("django", "django-api", "fastapi", "flask", "default")
        assert info.confidence in ("high", "medium", "low")
        assert isinstance(info.reason, str)

    def test_unknown_when_nothing_present(self, tmp_path):
        """Empty directory with no installed frameworks → unknown."""
        with patch("pymodules.detector._is_importable", return_value=False):
            info = detect_framework(tmp_path)
        assert info.name == "unknown"
        assert info.preset == "default"

    def test_detects_django_from_manage_py(self, tmp_path):
        (tmp_path / "manage.py").write_text("# django manage")
        with patch("pymodules.detector._is_importable", side_effect=lambda n: n == "django"):
            info = detect_framework(tmp_path)
        assert info.name == "django"
        assert info.preset == "django"
        assert info.confidence == "high"

    def test_detects_fastapi_from_import(self, tmp_path):
        with patch("pymodules.detector._is_importable", side_effect=lambda n: n == "fastapi"):
            info = detect_framework(tmp_path)
        assert info.name == "fastapi"
        assert info.preset == "fastapi"

    def test_detects_flask_from_import(self, tmp_path):
        with patch("pymodules.detector._is_importable", side_effect=lambda n: n == "flask"):
            info = detect_framework(tmp_path)
        assert info.name == "flask"
        assert info.preset == "flask"

    def test_detects_django_from_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("Django>=4.0\npsycopg2\n")
        with patch("pymodules.detector._is_importable", return_value=False):
            info = detect_framework(tmp_path)
        assert info.name == "django"
        assert info.confidence == "low"

    def test_detects_fastapi_from_pyproject_toml(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi>=0.95", "uvicorn"]\n'
        )
        with patch("pymodules.detector._is_importable", return_value=False):
            info = detect_framework(tmp_path)
        assert info.name == "fastapi"

    def test_django_wins_over_flask_by_priority(self, tmp_path):
        """When both Django and Flask are present, Django wins."""
        (tmp_path / "requirements.txt").write_text("Django>=4.0\nflask>=2.0\n")
        with patch(
            "pymodules.detector._is_importable",
            side_effect=lambda n: n in ("django", "flask"),
        ):
            info = detect_framework(tmp_path)
        assert info.name == "django"
        assert "flask" in info.all_detected

    def test_django_settings_env_boosts_confidence(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "myproject.settings")
        with patch("pymodules.detector._is_importable", side_effect=lambda n: n == "django"):
            info = detect_framework(tmp_path)
        assert info.name == "django"
        assert info.confidence == "high"

    def test_all_detected_populated(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("django\nfastapi\n")
        with patch("pymodules.detector._is_importable", return_value=False):
            info = detect_framework(tmp_path)
        assert len(info.all_detected) >= 1

    def test_unknown_preset_is_default(self, tmp_path):
        with patch("pymodules.detector._is_importable", return_value=False):
            info = detect_framework(tmp_path)
        assert info.preset == "default"

    def test_detects_django_api_preset_when_drf_is_importable(self, tmp_path):
        with patch(
            "pymodules.detector._is_importable",
            side_effect=lambda n: n in ("django", "rest_framework"),
        ):
            info = detect_framework(tmp_path)
        assert info.name == "django"
        assert info.preset == "django-api"

    def test_detects_django_api_preset_from_dependencies(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("Django>=4.0\ndjangorestframework>=3.14\n")
        with patch("pymodules.detector._is_importable", return_value=False):
            info = detect_framework(tmp_path)
        assert info.name == "django"
        assert info.preset == "django-api"
