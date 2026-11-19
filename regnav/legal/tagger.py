"""Rule-based statement authority tagger (D-044).

Labels (what a compliance user needs to know about one statement):

| label                     | meaning                                                         | answer section     |
|---------------------------|-----------------------------------------------------------------|--------------------|
| binding_requirement       | an obligation in law or a binding standard ("must", "shall")     | Mandatory          |
| binding_context           | text in binding law that is not an obligation (definitions,      | Mandatory, as      |
|                           | "APRA may", "should" inside a standard, commencement)            | context            |
| restates_law              | guidance stating what the law/standard requires                  | Mandatory, citing  |
|                           | (resolved to the primary provision where possible)               | the provision      |
| regulator_interpretation  | the regulator's view of what the law means or covers             | Regulator expects  |
|                           | ("the OAIC considers...", "in APRA's view")                       | (flagged)          |
| regulator_expectation     | supervisory expectations / better practice from a regulator      | Regulator expects  |
| voluntary_recommendation  | voluntary government guidance                                    | Recommended        |
| information               | descriptive text with no normative force                         | context only       |
| unclear                   | guidance using mandatory wording without identifying the law     | flagged: verify    |

Rules are ordered and every decision records the evidence pattern, so labels are auditable. An
LLM fallback for ``unclear`` can be added behind :func:`classify`, but is not used by default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from regnav.ingest.tag import classify_modality
from regnav.legal.references import Reference, extract_references

LABELS = (
    "binding_requirement",
    "binding_context",
    "restates_law",
    "regulator_interpretation",
    "regulator_expectation",
    "voluntary_recommendation",
    "information",
    "unclear",
)
LABEL_TO_SECTION = {
    "binding_requirement": "mandatory",
    "binding_context": "mandatory",
    "restates_law": "mandatory",
    "regulator_interpretation": "regulator_expects",
    "regulator_expectation": "regulator_expects",
    "voluntary_recommendation": "recommended",
    "information": None,
    "unclear": None,
}

_INTERPRETATION = re.compile(
    r"\b(the OAIC|OAIC|APRA|the Commissioner)\s+(considers|is of the view|takes the view|interprets)\b"
    r"|\b(in|from) (the OAIC'?s|APRA'?s|our) view\b"
    r"|\bwould generally (fall|be considered|constitute|be)\b|\bis likely to (constitute|fall within|be considered)\b"
    r"|\bAPRA does not intend\b|\bdoes not intend to capture\b",
    re.I,
)
_RESTATES = re.compile(
    r"\bmust comply with (APP|the APPs|the Australian Privacy Principles|the Privacy Act)\b"
    r"|\b(APP|Australian Privacy Principle)\s?\d+(\.\d+)?\s+(requires|prohibits|restricts|provides)\b"
    r"|\b(the )?Privacy Act (requires|applies|prohibits)\b"
    r"|\b(required|permitted|prohibited) (by|under) (the )?(Privacy Act|APP|CPS|Prudential Standard)"
    r"|\b(CPS|SPS)\s?\d{3} (requires|sets out|prohibits)\b|\bWhere CPS\s?\d{3} requires\b"
    r"|\bunder (APP|Australian Privacy Principle)\s?\d+(\.\d+)?,?\s+\w+(\s+\w+)?\s+(must|is required|are required)\b"
    r"|\bobligations? under (the )?(Privacy Act|APPs?|Australian Privacy Principles)\b"
    r"|\bthis is a collection of personal information and must\b"
    r"|\bprivacy obligations (will )?apply\b",
    re.I,
)
_EXPECTATION = re.compile(
    r"\bAPRA (expects|strongly encourages|encourages|requires regulated entities)\b|\bAPRA'?s expectations?\b"
    r"|\bthe OAIC (recommends|suggests|expects|encourages)\b|\b(good|better|sound|best) practice\b"
    r"|\b(a )?prudent (entity|institution|Board|board)\b|\bAPRA envisages\b",
    re.I,
)
_LAW_REF_INSTRUMENTS = ("APP", "Privacy Act", "CPS", "SPS")
_FOOTNOTE = re.compile(r"^\s*(\[\d+\]|\^?\[?\d{1,2}\]?\s+https?://|•?\s*\d{1,2}\s+https?://)")


@dataclass
class Tag:
    label: str
    confidence: str  # "high" (explicit pattern) | "medium" (wording + context) | "low" (fallback)
    evidence: str
    refs: list[Reference] = field(default_factory=list)


def classify(text: str, doc_tier: str, context: str = "") -> Tag:
    """Label one statement. ``context`` is its lead-in (governs list items)."""
    full = f"{context} {text}".strip()
    if _FOOTNOTE.match(text):
        return Tag("information", "high", "footnote / citation line", extract_references(text))
    refs = extract_references(full)
    law_refs = [r for r in refs if r.instrument.startswith(_LAW_REF_INSTRUMENTS)]
    modality = classify_modality(full)

    if doc_tier == "binding":
        if modality == "must":
            return Tag(
                "binding_requirement", "high", "mandatory wording in binding instrument", refs
            )
        return Tag("binding_context", "high", f"binding instrument, {modality} wording", refs)

    if (m := _INTERPRETATION.search(full)) is not None:
        return Tag(
            "regulator_interpretation", "high", f"interpretation phrase: {m.group(0)!r}", refs
        )
    if (m := _RESTATES.search(full)) is not None:
        return Tag("restates_law", "high", f"restates law: {m.group(0)!r}", refs)
    if doc_tier == "expectation":
        if modality == "must" and law_refs:
            return Tag("restates_law", "medium", "mandatory wording + citation of law", refs)
        if (m := _EXPECTATION.search(full)) is not None:
            return Tag("regulator_expectation", "high", f"expectation phrase: {m.group(0)!r}", refs)
        if modality == "should":
            return Tag(
                "regulator_expectation", "medium", "guidance with 'should'-type wording", refs
            )
        if modality == "must":
            return Tag(
                "unclear", "low", "mandatory wording in guidance without identifying the law", refs
            )
        return Tag("information", "medium", "no normative wording", refs)
    # voluntary tier
    if modality in ("must", "should"):
        return Tag(
            "voluntary_recommendation",
            "high" if modality == "should" else "medium",
            f"voluntary guidance, {modality} wording",
            refs,
        )
    return Tag("information", "medium", "no normative wording", refs)
