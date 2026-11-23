"""Use-case intake for the model-use check (D-053).

A short form a data scientist, actuary or analytics lead can fill in about one model or AI use.
The answers select which stages of ``data/playbooks.yaml`` apply. "Unsure" is treated as "yes"
(conservative): the item is included and flagged for the user to confirm.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

YesNoUnsure = Literal["yes", "no", "unsure"]


class UseCase(BaseModel):
    name: str = Field(description="Short name, e.g. 'Motor pricing GBM'")
    description: str = Field("", description="One or two sentences: what the model does, for whom")
    sector: Literal["bank", "insurer"] = "bank"
    team: Literal["data_science", "actuarial", "analytics", "data_engineering", "other"] = (
        "data_science"
    )
    lifecycle_stage: Literal["idea", "build", "validate", "deploy", "live"] = "build"
    personal_information: YesNoUnsure = Field(
        "unsure",
        description="Does it use personal information (training data, inputs, prompts or outputs)?",
    )
    sensitive_information: YesNoUnsure = Field(
        "no", description="Health, biometric or other sensitive information?"
    )
    decisions_about_individuals: YesNoUnsure = Field(
        "unsure",
        description="Does it make, or substantially inform, decisions about customers or people "
        "(pricing, underwriting, credit, claims, eligibility)?",
    )
    third_party: YesNoUnsure = Field(
        "unsure", description="Does it rely on an external vendor, model API or platform?"
    )
    offshore: YesNoUnsure = Field(
        "unsure", description="Are data, models or support staff located outside Australia?"
    )
    critical_operation: YesNoUnsure = Field(
        "unsure",
        description="Does it support a critical operation (e.g. claims, payments, pricing at scale)?",
    )
    generative_ai: YesNoUnsure = Field("no", description="Does it use generative AI or an LLM?")

    def facts(self) -> dict[str, Any]:
        """Flat facts for playbook / coverage conditions. Unsure counts as yes."""
        out: dict[str, Any] = {"sector": self.sector, "team": self.team, "always": True}
        for f in (
            "personal_information",
            "sensitive_information",
            "decisions_about_individuals",
            "third_party",
            "offshore",
            "critical_operation",
            "generative_ai",
        ):
            out[f] = getattr(self, f) in ("yes", "unsure")
        return out

    def unsure_fields(self) -> list[str]:
        return [
            name
            for name, field in type(self).model_fields.items()
            if field.annotation == YesNoUnsure and getattr(self, name) == "unsure"
        ]

    @classmethod
    def from_yaml(cls, path: str | Path) -> UseCase:
        return cls.model_validate(yaml.safe_load(Path(path).read_text()) or {})


FIELD_QUESTIONS: dict[str, str] = {
    name: str(f.description) for name, f in UseCase.model_fields.items() if f.description
}
