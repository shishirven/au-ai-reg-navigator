"""Home: what the tool is for, how to use it, how to read results, and what's in the library."""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

import streamlit as st

from regnav.commencement import for_doc
from regnav.config import load_config
from regnav.demo_guard import CORPUS_AS_OF, footer_text
from regnav.ingest.index import load_manifest
from regnav.library import LibraryDoc, library

ROOT = Path(__file__).resolve().parents[2]
TIER_STYLE = {
    "binding": (
        "Mandatory",
        "#d92d20",
        "Binding law: APRA prudential standards (and, when switched on, the Privacy Act).",
    ),
    "expectation": (
        "Regulator expects",
        "#dc6803",
        "Regulator guidance and letters. Not law in itself, but supervisors use it as the benchmark.",
    ),
    "voluntary": (
        "Recommended",
        "#079455",
        "Voluntary government guidance: good practice, not required.",
    ),
}
ISSUER_URL = {"APRA": "apra.gov.au", "OAIC": "oaic.gov.au"}

st.markdown(
    """
<style>
.block-container {max-width: 1080px; padding-top: 2.2rem;}
.h-hero {font-size:2.3rem; font-weight:780; line-height:1.15; margin:0 0 .5rem 0;}
.h-sub {font-size:1.1rem; opacity:.82; margin-bottom:1.2rem; max-width:52rem;}
.h-card {border:1px solid rgba(128,128,128,.22); border-radius:14px; padding:1.1rem 1.2rem;
  background:rgba(128,128,128,.04); height:100%;}
.h-card h3 {margin:.2rem 0 .35rem 0; font-size:1.2rem;}
.h-card p, .h-card li {font-size:.93rem; opacity:.88; margin:.15rem 0;}
.h-icon {font-size:2rem;}
.h-tag {display:inline-block; padding:.1rem .6rem; border-radius:999px; font-size:.78rem;
  font-weight:650; color:white; white-space:nowrap;}
.h-tier {display:flex; gap:.7rem; align-items:flex-start; margin:.35rem 0;}
.h-tier div {font-size:.93rem; opacity:.9;}
.h-note {font-size:.85rem; opacity:.72;}
.h-doc {border-bottom:1px solid rgba(128,128,128,.18); padding:.55rem 0;}
.h-doc b {font-size:.97rem;}
.h-doc .m {font-size:.84rem; opacity:.75;}
</style>
""",
    unsafe_allow_html=True,
)


def tag(tier: str) -> str:
    label, color, _ = TIER_STYLE[tier]
    return f'<span class="h-tag" style="background:{color}">{label}</span>'


def doc_row(d: LibraryDoc, today: date) -> str:
    when = ""
    if d.effective_from:
        if d.tier == "binding":
            future = d.effective_from > today.isoformat()
            when = f"{'commences' if future else 'in force from'} {d.effective_from}"
        else:
            when = f"dated {d.effective_from}"
    for c in for_doc(d.id, today):
        when += f" · explains {c.short}, which commences {c.long_date} ⏳"
    sectors = ", ".join(s.replace("any_business", "any business") for s in d.applies_to)
    link = f' · <a href="{html.escape(d.url)}" target="_blank">source ↗</a>' if d.url else ""
    return (
        f'<div class="h-doc">{tag(d.tier)} <b>{html.escape(d.title)}</b>'
        f'<div class="m">{html.escape(d.issuer)} · {html.escape(when)} · applies to {html.escape(sectors)}{link}</div></div>'
    )


# ----------------------------------------------------------------------------- hero / objective
st.markdown(
    '<div class="h-hero">⚖️ AU AI Regulation Navigator</div>'
    '<div class="h-sub">Find out which Australian regulatory requirements apply to the models and AI '
    "you build or buy, and how binding each one is, before you take the work to risk, compliance and "
    "privacy. Built for <b>data leads, data scientists, actuaries and analytics teams</b> at banks and "
    "insurers. Every statement is quoted from, and linked to, its source.</div>",
    unsafe_allow_html=True,
)

st.markdown("### Why it exists")
c1, c2 = st.columns([1.15, 1])
with c1:
    st.markdown(
        '- **The rules that govern AI rarely say "AI".** The binding ones are technology-neutral APRA '
        "standards about service providers, information security and operational risk, so a search "
        'for "AI vendor" misses them.\n'
        "- **Legal force gets mixed up.** Law, regulator expectations and voluntary guidance use "
        "similar words; treating guidance as law wastes effort, and treating law as guidance creates "
        "breaches.\n"
        "- **Data teams meet the rules last**, in risk review. A cited first pass earlier saves weeks."
    )
with c2:
    st.markdown("**Every item is labelled by legal force:**")
    for t, (_, _, desc) in TIER_STYLE.items():
        st.markdown(
            f'<div class="h-tier">{tag(t)}<div>{html.escape(desc)}</div></div>',
            unsafe_allow_html=True,
        )

# ----------------------------------------------------------------------------- the two tools
st.markdown("### Two ways to use it")
a, b = st.columns(2)
with a:
    st.markdown(
        '<div class="h-card"><div class="h-icon">🧭</div><h3>Model-use check</h3>'
        "<p><b>Use when:</b> you're building, buying or changing a specific model.</p>"
        "<p><b>You get:</b> a checklist by lifecycle stage (data, validation, monitoring, privacy, "
        "vendors…), each item quoted with its paragraph, the evidence teams usually produce and who "
        "signs off. Track status and export to CSV.</p>"
        "<p><b>Time:</b> about 2 minutes. No AI model writes it.</p></div>",
        unsafe_allow_html=True,
    )
    st.page_link("views/model_use_check.py", label="Start a model-use check", icon="➡️")
with b:
    st.markdown(
        '<div class="h-card"><div class="h-icon">💬</div><h3>Ask a question</h3>'
        '<p><b>Use when:</b> you have a specific question, e.g. <i>"Do we have to tell customers '
        'when a model informs a pricing decision?"</i></p>'
        "<p><b>You get:</b> an answer split into Mandatory / Regulator expects / Recommended, every "
        "sentence cited, and a note of anything outside the library.</p>"
        "<p><b>Time:</b> about 30 seconds. Written by an AI model, then checked by rules.</p></div>",
        unsafe_allow_html=True,
    )
    st.page_link("views/ask.py", label="Ask a question", icon="➡️")

# ----------------------------------------------------------------------------- how to use
st.markdown("### How to use it")
t1, t2, t3 = st.tabs(["🧭 Model-use check", "💬 Ask a question", "🔎 Reading the results"])
with t1:
    st.markdown(
        "1. Open **Model-use check** and click **Start with my model**, or open one of the examples.\n"
        "2. Give the model a name and choose your organisation, team and lifecycle stage.\n"
        "3. Answer 5–7 quick questions with **Yes / No / Not sure**. *Not sure* counts as yes and is "
        "flagged, so nothing is silently left out.\n"
        "4. **Check your answers**, change anything that's wrong, then **Build my checklist**.\n"
        "5. Read **What stands out** first (APRA notifications, dates that are coming up).\n"
        "6. Work through each stage: set **Met / Not met / N/A**, add an owner and an evidence link.\n"
        "7. **Export** the CSV (to keep tracking) and the report (to attach to your risk assessment "
        "or model inventory entry), then take it to your risk partner for review."
    )
    st.caption("Statuses live in your browser session only: export to keep them.")
with t2:
    st.markdown(
        "1. Open **Ask a question** and pick your sector in the sidebar.\n"
        "2. Ask one clear question. Name the activity rather than the technology where you can: "
        '*"engaging a vendor that hosts our model"* finds more than *"using AI"*.\n'
        "3. Read the answer by section, and open **Sources** on the right to see each quoted paragraph.\n"
        "4. Check the **Not covered by this library** line for topics to take elsewhere.\n"
        "5. Treat it as a cited first pass: confirm against the source with your compliance team."
    )
    st.caption(
        "The public demo limits questions per session and logs them for quality monitoring: don't "
        "enter confidential details."
    )
with t3:
    st.markdown(
        "| you see | it means |\n|---|---|\n"
        f"| {TIER_STYLE['binding'][0]} | a binding requirement in an APRA prudential standard |\n"
        f"| {TIER_STYLE['expectation'][0]} | what APRA or the OAIC expects; not law in itself |\n"
        f"| {TIER_STYLE['voluntary'][0]} | voluntary good practice |\n"
        "| ⚖️ explains binding law | guidance that explains a law (e.g. the Privacy Act): the underlying obligation is binding even though the guidance isn't |\n"
        "| ⏳ from a date | the requirement isn't in force yet; note when it starts |\n"
        "| ❔ weaker match | a looser match: check whether it applies to you |\n"
        "| Not covered by this library | relevant rules this tool doesn't hold (e.g. FAR, insurance or credit law): check separately |"
    )

# ----------------------------------------------------------------------------- the library
st.markdown("### What's in the library")
lib = library(ROOT)
today = date.today()
st.markdown(
    f"**{len(lib['current'])} documents are searched**, retrieved {CORPUS_AS_OF}. Answers and "
    "checklists only use these; anything else is named as *not covered*."
)
st.markdown("".join(doc_row(d, today) for d in lib["current"]), unsafe_allow_html=True)
with st.expander(f"Kept for history, not used in answers ({len(lib['superseded'])})"):
    st.markdown(
        "Earlier versions and replaced guidance, indexed so changes can be compared but excluded "
        "from answers and checklists."
    )
    st.markdown("".join(doc_row(d, today) for d in lib["superseded"]), unsafe_allow_html=True)
if lib["staged"]:
    with st.expander(
        f"Coming next: Privacy Act text, staged and not yet searched ({len(lib['staged'])})"
    ):
        st.markdown(
            "Verified extracts of the Privacy Act. Until they are switched on, privacy obligations "
            "appear under *Regulator expects* (via OAIC guidance) with an ⚖️ *explains binding law* "
            "note, rather than under *Mandatory*."
        )
        st.markdown("".join(doc_row(d, today) for d in lib["staged"]), unsafe_allow_html=True)
st.markdown(
    '<p class="h-note">Not in the library (named in answers when relevant): the Financial '
    "Accountability Regime, CPS 510 Governance, CPG 234, superannuation standards (SPS), ASIC guidance "
    "and the Corporations Act, insurance and consumer-credit law, anti-discrimination law, and "
    "actuarial professional standards.</p>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------- limits
st.markdown("### Good to know")
st.markdown(
    "- **Not legal advice, and never a compliance verdict.** It shows what to check and where it "
    "says so; your risk, compliance and privacy teams decide.\n"
    "- **Assumes an APRA-regulated bank or insurer.** Superannuation trustees and other organisations "
    "are out of scope for now.\n"
    "- **A fixed snapshot.** Check the source links for later changes.\n"
    "- **Validated, provisionally.** Quality is measured on developer-written test questions; an "
    "expert-reviewed set is next. Methods and results are in the project's validation report."
)

try:
    idx = (load_manifest(load_config()) or {}).get("index_version", "not built")
except Exception:
    idx = "not built"
st.caption(footer_text(idx))
