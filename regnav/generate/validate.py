"""Post-hoc validation of structured answers.

Checks (each failure is a human-readable error string):
  * JSON parses and matches the schema
  * every claim has a citation and the cited id is in the retrieved set
  * section/tier consistency: mandatory<-binding, regulator_expects<-expectation, recommended<-voluntary
  * modality: nothing under `mandatory` may cite a `should` chunk; no claim anywhere may use
    mandatory language (must / required / mandatory / shall) when citing a `should` chunk
  * abstention is coherent (abstained <=> no claims)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from regnav.config import SECTION_TO_TIER
from regnav.generate.schema import StructuredAnswer

_MANDATORY_WORDS = re.compile(r"\b(must|required|mandatory|shall|obliged|obligated)\b", re.I)
_NEGATED = re.compile(
    r"\b(not|no)\s+(legally\s+)?(required|mandatory|obliged)\b|\bneed\s+not\b", re.I
)


@dataclass
class ValidationResult:
    ok: bool
    answer: StructuredAnswer | None
    errors: list[str] = field(default_factory=list)
    error_types: list[str] = field(default_factory=list)

    def add(self, kind: str, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)
        self.error_types.append(kind)


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def uses_mandatory_language(claim: str) -> bool:
    return bool(_MANDATORY_WORDS.search(_NEGATED.sub(" ", claim)))


def validate_answer(raw: str, retrieved: dict[str, dict[str, Any]]) -> ValidationResult:
    """``retrieved``: chunk_id -> metadata (needs ``tier`` and ``modality``)."""
    res = ValidationResult(ok=True, answer=None)
    try:
        data = _extract_json(raw)
    except (json.JSONDecodeError, TypeError):
        res.add("parse", "Output is not valid JSON.")
        return res
    try:
        answer = StructuredAnswer.model_validate(data)
    except ValidationError as e:
        res.add(
            "schema",
            f"Output does not match the schema: {e.errors()[0]['msg']} at {e.errors()[0]['loc']}.",
        )
        return res
    res.answer = answer
    claims = answer.claims()
    if answer.abstained and claims:
        res.add(
            "abstain",
            "abstained is true but claims were given; either abstain with empty sections or answer.",
        )
    if not answer.abstained and not claims:
        res.add(
            "abstain",
            "No claims given; if the sources do not answer the question set abstained to true.",
        )
    for section, c in claims:
        cid = c.citation_id.strip()
        if not cid:
            res.add("citation_missing", f"Claim in {section} has no citation: {c.claim[:60]!r}")
            continue
        meta = retrieved.get(cid)
        if meta is None:
            res.add("citation_invalid", f"Citation {cid!r} is not one of the provided source ids.")
            continue
        expected_tier = SECTION_TO_TIER[section]
        if meta.get("tier") != expected_tier:
            res.add(
                "tier_mismatch",
                f"Claim in `{section}` cites {cid} whose tier is {meta.get('tier')}; "
                f"`{section}` may only cite {expected_tier} sources.",
            )
        modality = meta.get("modality")
        if section == "mandatory" and modality == "should":
            res.add(
                "modality",
                f"Claim in `mandatory` cites {cid}, which is 'should' guidance, not a requirement.",
            )
        elif modality == "should" and uses_mandatory_language(c.claim):
            res.add(
                "modality",
                f"Claim citing {cid} ('should' guidance) uses mandatory language: {c.claim[:80]!r}",
            )
    return res
