"""Model-use check on the real index (D-053): each example use case must surface the provisions a
reviewer would expect, and must not surface vendor rules when there is no vendor.

Needs the real index (`make ingest`) and the cross-encoder; skipped otherwise. No LLM, no network.
Run: make test-corpus
"""

from __future__ import annotations

import pytest

from regnav.assess import UseCase, run_check
from regnav.config import load_config
from regnav.ingest.index import load_manifest
from regnav.retrieve import build_retrieval

pytestmark = pytest.mark.slow

# For each use case: groups of chunk ids (or "doc:<doc_id>"); each group must be hit.
EXPECTED = {
    "motor_pricing_gbm": {
        "vendor due diligence": ["apra_cps230_2026:p52"],
        "contract terms": ["apra_cps230_2026:p53", "apra_cps230_2026:p54"],
        "notify APRA": ["apra_cps230_2026:p60"],
        "vendor security": ["apra_cps234:p16", "apra_cps234:p22"],
        "ADM transparency fact sheet": ["doc:oaic_app1_adm_2026"],
        "data quality": ["doc:apra_cpg235"],
        "APRA AI letter": ["doc:apra_ai_letter_2026"],
        "critical operations / BCP": [
            "apra_cps230_2026:p39",
            "apra_cps230_2026:p41",
            "apra_cps230_2026:p32",
        ],
    },
    "genai_complaints_assistant": {
        "vendor due diligence": ["apra_cps230_2026:p52"],
        "notify APRA (offshoring)": ["apra_cps230_2026:p60"],
        "information security": ["apra_cps234:p21", "apra_cps234:p16"],
        "OAIC AI products guidance": ["doc:oaic_ai_products_2025"],
        "AI threats (APRA AI letter)": ["apra_ai_letter_2026:s004.1", "apra_ai_letter_2026:s004.2"],
    },
    "churn_propensity_internal": {
        "ADM transparency fact sheet": ["doc:oaic_app1_adm_2026"],
        "OAIC AI products guidance": ["doc:oaic_ai_products_2025"],
        "data quality": ["doc:apra_cpg235"],
    },
}
ABSENT = {"churn_propensity_internal": ["apra_cps230_2026:p52", "apra_cps230_2026:p60"]}


@pytest.fixture(scope="module")
def system():
    cfg = load_config()
    if load_manifest(cfg) is None:
        pytest.skip("real corpus not indexed - run `make ingest`")
    return cfg, build_retrieval(cfg)


@pytest.mark.parametrize("name", list(EXPECTED))
def test_example_use_case_surfaces_expected_provisions(system, name: str) -> None:
    cfg, sysm = system
    cl = run_check(UseCase.from_yaml(f"data/use_cases/{name}.yaml"), cfg, sysm)
    ids = {i.chunk_id for i in cl.items}
    docs = {i.chunk_id.split(":")[0] for i in cl.items}
    missing = [
        g
        for g, members in EXPECTED[name].items()
        if not any((m[4:] in docs) if m.startswith("doc:") else (m in ids) for m in members)
    ]
    assert not missing, f"{name}: missing {missing}"
    assert not ids & set(ABSENT.get(name, [])), f"{name}: vendor rules without a vendor"
    assert cl.counts()["binding"] > 0 or name == "churn_propensity_internal"
