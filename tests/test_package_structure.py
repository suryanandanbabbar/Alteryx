"""Tests for package discovery and application structure integrity."""

import sys
import pytest


def test_awa_package_imports():
    """Verify top-level 'awa' package is discovered and importable."""
    import awa
    assert awa.__file__ is not None
    from awa.parser.format_handler import FormatValidationError
    from awa.analysis.workflow_analyzer import analyze_canonical
    from awa.generators.svg_generator import generate_svg
    from awa.translators.registry import get_translator
    assert FormatValidationError is not None
    assert analyze_canonical is not None
    assert generate_svg is not None
    assert get_translator is not None


def test_fastapi_application_imports():
    """Verify backend FastAPI application is importable."""
    from backend.app.main import app
    assert app is not None
    assert app.title == "AWA — Alteryx Workflow Analyzer & Python Translator API"


def test_no_inconsistent_import_paths():
    """Verify no modules rely on 'backend.src' or relative package breakouts."""
    with pytest.raises(ModuleNotFoundError):
        import backend.src.awa  # type: ignore # noqa: F401
