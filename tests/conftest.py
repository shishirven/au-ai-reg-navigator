from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from regnav.fixtures import build_fixture_pdfs

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_raw_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Fixture corpus rendered to PDFs in a temp raw dir."""
    out = tmp_path_factory.mktemp("raw")
    build_fixture_pdfs(FIXTURES / "corpus", out)
    return out


@pytest.fixture()
def fixture_sources(tmp_path: Path) -> Path:
    dst = tmp_path / "sources.yaml"
    shutil.copy(FIXTURES / "sources.yaml", dst)
    return dst
