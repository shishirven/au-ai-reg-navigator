"""Checklist -> Markdown (to read or attach to a risk assessment) and CSV (to track status)."""

from __future__ import annotations

import csv
import io

from regnav.assess.checklist import Checklist, ChecklistItem

TIER_MARK = {
    "binding": "🔴 Mandatory",
    "expectation": "🟠 Regulator expects",
    "voluntary": "🟢 Recommended",
}
CSV_FIELDS = [
    "stage",
    "playbook",
    "tier",
    "document",
    "citation",
    "requirement_excerpt",
    "modality",
    "effective_from",
    "not_yet_in_force",
    "weak_match",
    "explains_binding_law",
    "also_relevant_to",
    "evidence_typically_produced",
    "involve",
    "status",
    "evidence_link",
    "owner",
    "notes",
    "chunk_id",
    "source_url",
]
DISCLAIMER = (
    "General information from public regulatory documents, not legal advice and not a compliance "
    "verdict. Confirm each item against the cited source with your risk, compliance and privacy teams."
)


def _flags(i: ChecklistItem) -> str:
    out = []
    if i.not_yet_in_force:
        out.append(f"⏳ from {i.effective_from}")
    if i.explains_law:
        out.append("⚖️ explains binding law")
    if i.weak:
        out.append("❔ weaker match, check relevance")
    if i.also_in:
        out.append("also: " + "; ".join(i.also_in))
    return f" · {' · '.join(out)}" if out else ""


def to_markdown(cl: Checklist) -> str:
    uc = cl.use_case
    n = cl.counts()
    lines = [
        f"# Model-use check: {uc.name}",
        "",
        f"*{uc.description}*" if uc.description else "",
        "",
        "| | |",
        "|---|---|",
        f"| Sector / team / stage | {uc.sector} · {uc.team.replace('_', ' ')} · {uc.lifecycle_stage} |",
        f"| Personal information · sensitive | {uc.personal_information} · {uc.sensitive_information} |",
        f"| Decisions about individuals | {uc.decisions_about_individuals} |",
        f"| Third party · offshore | {uc.third_party} · {uc.offshore} |",
        f"| Critical operation · generative AI | {uc.critical_operation} · {uc.generative_ai} |",
        "",
        f"**{n['binding']} mandatory · {n['expectation']} regulator-expects · {n['voluntary']} "
        f"recommended items** across {len(cl.stages)} stages.",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Key points for this use case",
        "",
    ]
    lines += [f"- {x}" for x in cl.notes + cl.assumptions]
    for s in cl.stages:
        lines += ["", f"## {s.stage.title}", f"*{s.playbook_title}*", ""]
        if s.stage.evidence:
            lines.append(f"**Evidence typically produced:** {s.stage.evidence}  ")
        if s.stage.involve:
            lines.append(f"**Usually involves:** {', '.join(s.stage.involve)}")
        lines.append("")
        if not s.has_binding:
            gap = (
                " Privacy Act obligations apply, but the Act's text is not yet live in this library: "
                "see the ⚖️ notes and *Not covered* below."
                if s.playbook_id in ("personal_info", "automated_decisions")
                else ""
            )
            lines.append(f"*No binding paragraph in this library matched this stage.{gap}*")
            lines.append("")
        if s.see_also:
            refs = "; ".join(
                dict.fromkeys(f"{i.document} {i.citation}".strip() for i in s.see_also)
            )
            lead = (
                "Covered by items listed above" if not s.items else "Also relevant (listed above)"
            )
            lines.append(f"- {lead}: {refs}")
        for i in s.items:
            lines.append(
                f"- [ ] **{TIER_MARK.get(i.tier, i.tier)}** · {i.document} {i.citation}{_flags(i)}  \n"
                f"  {i.excerpt}"
            )
    if cl.gaps:
        lines += ["", "## Not covered by this library: check separately", ""]
        lines += [f"- **{g.title}.** {g.note}" for g in cl.gaps]
    lines += [
        "",
        "---",
        f"Generated {cl.generated.isoformat()} · config `{cl.config_name}` · index `{cl.index_version}` · "
        "no language model used: every item quotes its cited source.",
    ]
    return "\n".join(x for x in lines if x is not None) + "\n"


def to_csv(cl: Checklist) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    w.writeheader()
    for s in cl.stages:
        for i in s.items:
            w.writerow(
                {
                    "stage": s.stage.title,
                    "playbook": s.playbook_title,
                    "tier": i.tier_label,
                    "document": i.document,
                    "citation": i.citation,
                    "requirement_excerpt": i.excerpt,
                    "modality": i.modality,
                    "effective_from": i.effective_from,
                    "not_yet_in_force": "yes" if i.not_yet_in_force else "",
                    "weak_match": "yes" if i.weak else "",
                    "explains_binding_law": i.explains_law,
                    "also_relevant_to": "; ".join(i.also_in),
                    "evidence_typically_produced": s.stage.evidence,
                    "involve": ", ".join(s.stage.involve),
                    "status": "",
                    "evidence_link": "",
                    "owner": "",
                    "notes": "",
                    "chunk_id": i.chunk_id,
                    "source_url": i.url,
                }
            )
    return buf.getvalue()
