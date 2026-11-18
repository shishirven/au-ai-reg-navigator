"""Structured answer schema (shared by prompt, LLM structured-output and validator)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SECTIONS = ("mandatory", "regulator_expects", "recommended")
DISCLAIMER = (
    "This is general information generated from public regulatory documents, not legal advice. "
    "Confirm obligations against the source documents and seek professional advice for your circumstances."
)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str = Field(min_length=1)
    citation_id: str = Field(min_length=1)


class StructuredAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mandatory: list[Claim] = Field(default_factory=list)
    regulator_expects: list[Claim] = Field(default_factory=list)
    recommended: list[Claim] = Field(default_factory=list)
    abstained: bool = False
    abstain_reason: str = ""

    def claims(self) -> list[tuple[str, Claim]]:
        return [(s, c) for s in SECTIONS for c in getattr(self, s)]


def answer_json_schema() -> dict[str, Any]:
    """Plain JSON schema (no $refs) accepted by Ollama `format` and Anthropic output_config."""
    claim = {
        "type": "object",
        "properties": {"claim": {"type": "string"}, "citation_id": {"type": "string"}},
        "required": ["claim", "citation_id"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "mandatory": {"type": "array", "items": claim},
            "regulator_expects": {"type": "array", "items": claim},
            "recommended": {"type": "array", "items": claim},
            "abstained": {"type": "boolean"},
            "abstain_reason": {"type": "string"},
        },
        "required": [
            "mandatory",
            "regulator_expects",
            "recommended",
            "abstained",
            "abstain_reason",
        ],
        "additionalProperties": False,
    }
