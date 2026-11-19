"""Binding on whom, and from when (D-044).

Combines the user's profile (sector; for privacy law, whether the business is an APP entity) with
a provision's regime, effective date and status. The small business exemption follows the
Privacy Act text in the corpus (s 6C(1): an "organisation" excludes a small business operator;
s 6D: $3,000,000 annual-turnover test and exceptions; s 6EA: opting in).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

SB_EXCEPTIONS = {
    "health_service": "provides a health service and holds health information (s 6D(4)(b))",
    "trades_in_personal_info": "discloses or collects personal information for a benefit, service or advantage (s 6D(4)(c)-(d))",
    "commonwealth_contractor": "is a contracted service provider for a Commonwealth contract (s 6D(4)(e))",
    "credit_reporting_body": "is a credit reporting body (s 6D(4)(f))",
    "related_to_larger_body": "is related to a body corporate that carries on a business that is not a small business (s 6D(9))",
    "opted_in": "has chosen to be treated as an organisation (s 6EA)",
}

Status = Literal[
    "applies", "applies_from", "likely_exempt", "not_applicable", "historical", "check"
]


@dataclass
class Profile:
    """What we know about the user's organisation. ``None`` = not stated."""

    sector: str | None = None  # bank | insurer | super | any_business
    turnover_over_3m: bool | None = None  # annual turnover > $3,000,000 (s 6D(1))
    exceptions: set[str] = field(default_factory=set)  # keys of SB_EXCEPTIONS that apply


@dataclass
class Applicability:
    status: Status
    reason: str
    from_date: str = ""


def app_entity_status(profile: Profile) -> tuple[str, str]:
    """('yes' | 'no' | 'unknown', reason) - is the organisation bound by the APPs?"""
    hits = [SB_EXCEPTIONS[e] for e in sorted(profile.exceptions) if e in SB_EXCEPTIONS]
    if profile.turnover_over_3m is True:
        return (
            "yes",
            "annual turnover above $3,000,000, so not a small business operator (s 6D(1), 6C(1))",
        )
    if hits:
        return "yes", "not a small business operator because it " + "; ".join(hits)
    if profile.turnover_over_3m is False:
        return "no", (
            "a business with annual turnover of $3,000,000 or less is generally a small business "
            "operator and not an APP entity (s 6D, 6C(1)), unless an exception in s 6D(4)/(9) or s 6EA applies"
        )
    if profile.sector in ("bank", "insurer", "super"):
        return "yes", (
            "assumed for an APRA-regulated entity (turnover well above $3,000,000 is typical); "
            "confirm against s 6D"
        )
    return (
        "unknown",
        "depends on annual turnover ($3,000,000 test, s 6D) and the s 6D(4) exceptions",
    )


def assess(
    *,
    regime: str,
    doc_tier: str,
    status: str,
    effective_from: str,
    applies_to_sector: bool,
    profile: Profile,
    today: date | None = None,
) -> Applicability:
    """Whether a provision is binding on this user, now or from a date."""
    today = today or date.today()
    if status == "superseded":
        return Applicability("historical", "superseded version; shown for history only")
    if not applies_to_sector:
        return Applicability(
            "not_applicable", f"does not apply to the {profile.sector or 'selected'} sector"
        )
    if doc_tier != "binding":
        base = Applicability("check", "guidance: not itself binding")
    else:
        base = Applicability("applies", "binding")
    if regime == "privacy":
        who, why = app_entity_status(profile)
        if who == "no":
            return Applicability("likely_exempt", f"Privacy Act obligations: {why}")
        if who == "unknown":
            base = Applicability("check", f"Privacy Act obligations apply to APP entities; {why}")
        else:
            base = Applicability(base.status, f"{base.reason}; applies to APP entities - {why}")
    if effective_from:
        try:
            eff = date.fromisoformat(effective_from)
        except ValueError:
            eff = None
        if eff and eff > today and base.status in ("applies", "check"):
            return Applicability(
                "applies_from",
                f"{base.reason}; not yet in force - commences {eff.isoformat()}",
                eff.isoformat(),
            )
    return base
