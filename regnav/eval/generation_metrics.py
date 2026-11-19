"""Rule-based generation metrics (no LLM). Computed on the final answer (what users see) and
on the model's first raw attempt (model reliability before validation/repair)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from regnav.config import SECTION_TO_TIER, TIER_TO_SECTION
from regnav.generate.schema import StructuredAnswer
from regnav.generate.validate import _extract_json, uses_mandatory_language


def parse_raw(raw: str) -> StructuredAnswer | None:
    try:
        return StructuredAnswer.model_validate(_extract_json(raw))
    except Exception:
        return None


def claim_metrics(
    answer: StructuredAnswer | None, retrieved: dict[str, dict[str, Any]]
) -> dict[str, float | None]:
    """citation_validity, authority_label_accuracy, modality_error_rate for one answer.
    None when the answer has no claims (abstained) or could not be parsed."""
    if answer is None:
        return {
            "citation_validity": None,
            "authority_label_accuracy": None,
            "modality_error_rate": None,
            "n_claims": 0,
        }
    claims = answer.claims()
    if not claims:
        return {
            "citation_validity": None,
            "authority_label_accuracy": None,
            "modality_error_rate": None,
            "n_claims": 0,
        }
    valid = [(s, c) for s, c in claims if c.citation_id in retrieved]
    label_ok = sum(
        1 for s, c in valid if retrieved[c.citation_id].get("tier") == SECTION_TO_TIER[s]
    )
    modality_err = 0
    for s, c in claims:
        meta = retrieved.get(c.citation_id)
        if meta is None or meta.get("modality") != "should":
            continue
        if s == "mandatory" or uses_mandatory_language(c.claim):
            modality_err += 1
    return {
        "citation_validity": len(valid) / len(claims),
        "authority_label_accuracy": (label_ok / len(valid)) if valid else None,
        "modality_error_rate": modality_err / len(claims),
        "n_claims": len(claims),
    }


def tier_recall(answer: StructuredAnswer, expected_tiers: Sequence[str]) -> float | None:
    """Share of expected tiers that appear as a non-empty answer section."""
    if not expected_tiers:
        return None
    present = {SECTION_TO_TIER[s] for s, _ in answer.claims()}
    return len(present & set(expected_tiers)) / len(set(expected_tiers))


def abstention_scores(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    """Positive class = 'should abstain' (unanswerable). Precision: of abstentions, how many were
    on unanswerable questions; recall: of unanswerable questions, how many were abstained."""
    tp = sum(1 for r in rows if r["abstained"] and not r["answerable"])
    fp = sum(1 for r in rows if r["abstained"] and r["answerable"])
    fn = sum(1 for r in rows if not r["abstained"] and not r["answerable"])
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return {"abstention_precision": precision, "abstention_recall": recall}


__all__ = ["TIER_TO_SECTION", "abstention_scores", "claim_metrics", "parse_raw", "tier_recall"]
