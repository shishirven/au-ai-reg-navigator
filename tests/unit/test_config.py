from pathlib import Path

import pytest

from regnav.config import SECTION_TO_TIER, TIER_TO_SECTION, load_config

CONFIGS = sorted(Path("configs").glob("*_*.yaml"))


@pytest.mark.parametrize(
    "path", [p for p in CONFIGS if "thresholds" not in p.name], ids=lambda p: p.stem
)
def test_experiment_configs_load(path: Path) -> None:
    cfg = load_config(path)
    assert cfg.name == path.stem
    assert cfg.generation.model  # model names come from config, not code
    assert cfg.judge.model != cfg.generation.model  # judge differs from generator


def test_retrieval_modes_differ_but_share_index() -> None:
    cfgs = [
        load_config(f"configs/{n}.yaml")
        for n in ("baseline_dense", "hybrid_pooled", "hybrid_stratified")
    ]
    assert [c.retrieval.mode for c in cfgs] == ["dense", "hybrid", "stratified"]
    assert len({c.index_key() for c in cfgs}) == 1


def test_section_tier_maps_are_inverse() -> None:
    assert {v: k for k, v in TIER_TO_SECTION.items()} == SECTION_TO_TIER


def test_flat_params_has_no_secrets() -> None:
    params = load_config("configs/hybrid_stratified.yaml").flat_params()
    assert not any("key" in k.lower() for k in params)


def test_overrides() -> None:
    cfg = load_config("configs/hybrid_stratified.yaml", name="x")
    assert cfg.name == "x"


def test_prod_config_matches_the_default_without_a_local_fallback() -> None:
    """Public-demo config keeps the default config's retrieval and quality knobs (D-057);
    only the outage behaviour changes."""
    prod = load_config("configs/prod.yaml")
    base = load_config()  # the default config
    assert base.name == "hybrid_stratified_capped"
    assert prod.name == "prod"
    assert prod.index_key() == base.index_key()
    assert prod.embedding.model_dump() == base.embedding.model_dump()
    assert prod.chunking.model_dump() == base.chunking.model_dump()
    assert prod.retrieval.model_dump() == base.retrieval.model_dump()
    fb = prod.generation.fallback
    assert fb is not None
    assert fb.provider == "openai_compat"
    assert fb.model == "gemini-3.8-flash"
    assert fb.api_key_env == "GEMINI_API_KEY"
    assert "generativelanguage.googleapis.com" in fb.base_url
    assert prod.generation.max_rate_limit_retries == 1
    assert prod.generation.timeout_s == 45.0
    excluded = {"fallback", "max_rate_limit_retries", "timeout_s"}
    assert prod.generation.model_dump(exclude=excluded) == base.generation.model_dump(
        exclude=excluded
    )
    assert prod.judge.model_dump() == base.judge.model_dump()
