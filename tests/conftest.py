from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from regnav.config import AppConfig, EmbeddingConfig, GenerationConfig, PathsConfig
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


def make_fixture_config(tmp_path: Path, raw_dir: Path, **overrides) -> AppConfig:
    """Config pointing at a private copy of the fixture corpus, hashing embedder."""
    raw = tmp_path / "raw"
    if not raw.exists():
        shutil.copytree(raw_dir, raw)
    sources = tmp_path / "sources.yaml"
    if not sources.exists():
        shutil.copy(FIXTURES / "sources.yaml", sources)
    data = {
        "name": "fixture",
        "embedding": EmbeddingConfig(backend="hashing", dim=256),
        # hashing-embedder similarities are not on BGE's scale: disable the similarity floor
        "generation": GenerationConfig(provider="stub", min_dense_similarity=0.0),
        "paths": PathsConfig(
            raw_dir=raw,
            sources_file=sources,
            chroma_dir=tmp_path / "chroma",
            eval_questions=FIXTURES / "questions.jsonl",
            mlruns_dir=tmp_path / "mlruns",
            results_dir=tmp_path / "results",
        ),
    }
    data.update(overrides)
    return AppConfig(**data)


@pytest.fixture()
def fixture_cfg(tmp_path: Path, fixture_raw_dir: Path) -> AppConfig:
    return make_fixture_config(tmp_path, fixture_raw_dir)
