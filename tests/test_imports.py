import importlib
import os
import sys

import pytest

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_third_party_imports():
    for module in ("PyQt6", "qfluentwidgets", "pypdf", "vtracer"):
        importlib.import_module(module)


def test_comtypes_import():
    if sys.platform != "win32":
        pytest.skip("comtypes is Windows-only")
    importlib.import_module("comtypes")


def test_core_modules_import():
    from core.engines.office import WordEngine, PowerPointEngine
    from core.features.image.image_vectorizer import ImageVectorizer

    assert WordEngine is not None
    assert PowerPointEngine is not None
    assert ImageVectorizer is not None
