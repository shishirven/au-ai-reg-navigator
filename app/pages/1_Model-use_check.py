"""Model-use check page (D-053): describe one model or AI use -> requirement checklist.

For data leads, data scientists, actuaries and analytics teams. No language model is called:
every item quotes its cited paragraph, so the page uses no API quota and gives the same answer
every time.
"""

from __future__ import annotations

import html
import os
from pathlib import Path

import streamlit as st

from regnav.assess import UseCase, run_check
from regnav.assess.checklist import Checklist
from regnav.assess.render import DISCLAIMER, TIER_MARK, to_csv, to_markdown
from regnav.assess.usecase import FIELD_QUESTIONS
from regnav.config import load_config
from regnav.demo_guard import footer_text, password_required, public_demo_enabled
from regnav.retrieve import build_retrieval

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/hybrid_stratified_rerank.yaml"
EXAMPLES = {
    "(blank)": None,
    "Actuarial: motor pricing model on a cloud ML platform": "data/use_cases/motor_pricing_gbm.yaml",
    "Data science: complaints summariser using an LLM API": "data/use_cases/genai_complaints_assistant.yaml",
    "Analytics: in-house churn model driving retention offers": "data/use_cases/churn_propensity_internal.yaml",
}
TEAMS = {
    "Data science / ML": "data_science",
    "Actuarial": "actuarial",
    "Analytics / BI": "analytics",
    "Data engineering": "data_engineering",
    "Other": "other",
}
TIER_COLOR = {"binding": "#b42318", "expectation": "#b54708", "voluntary": "#027a48"}

st.set_page_config(page_title="Model-use check", page_icon="🧭", layout="wide")
demo = public_demo_enabled()

if password_required() and not st.session_state.get("demo_authed"):
    st.info("Sign in on the main page first.")
    st.stop()


@st.cache_resource(show_spinner="Loading index and re-ranker...")
def get_system(config_path: str):
    os.chdir(ROOT)
    cfg = load_config(config_path)
    return cfg, build_retrieval(cfg)


config_path = (os.environ.get("REGNAV_CONFIG") or "configs/prod.yaml") if demo else DEFAULT_CONFIG
try:
    cfg, system = get_system(config_path)
except FileNotFoundError as e:
    st.error(f"{e}. Build the index first: `make ingest`.")
    st.stop()

st.title("🧭 Model-use check")
st.markdown(
    "For **data leads, data scientists, actuaries and analytics teams** at banks and insurers. "
    "Describe one model or AI use. You get the requirements and expectations to check, grouped by "
    "stage of the model lifecycle, each quoting its source paragraph, with the evidence teams "
    "typically produce and who usually signs off. Take the result to your risk partner. "
    "It is a starting point, **not a compliance verdict**."
)

example = st.selectbox("Start from an example (optional)", list(EXAMPLES))
base = UseCase.from_yaml(ROOT / EXAMPLES[example]) if EXAMPLES[example] else UseCase(name="")
YNU = ["yes", "no", "unsure"]

with st.form("use_case"):
    c1, c2 = st.columns([2, 1])
    name = c1.text_input("Model or use case name", base.name, max_chars=120)
    sector = c2.selectbox(
        "Your organisation", ["bank", "insurer"], ["bank", "insurer"].index(base.sector)
    )
    description = st.text_area(
        "What it does, for whom (1-2 sentences)", base.description, max_chars=600, height=80
    )
    c1, c2 = st.columns(2)
    team = c1.selectbox("Your team", list(TEAMS), list(TEAMS.values()).index(base.team))
    lifecycle = c2.selectbox(
        "Lifecycle stage",
        ["idea", "build", "validate", "deploy", "live"],
        ["idea", "build", "validate", "deploy", "live"].index(base.lifecycle_stage),
    )
    answers = {}
    left, right = st.columns(2)
    groups = [
        (
            left,
            "**Data and decisions**",
            [
                "personal_information",
                "sensitive_information",
                "decisions_about_individuals",
                "generative_ai",
            ],
        ),
        (right, "**Vendors and operations**", ["third_party", "offshore", "critical_operation"]),
    ]
    for col, heading, fields in groups:
        col.markdown(heading)
        for f in fields:
            answers[f] = col.radio(
                FIELD_QUESTIONS[f], YNU, YNU.index(getattr(base, f)), horizontal=True, key=f"q_{f}"
            )
    st.caption("'Unsure' is treated as 'yes': the item is included and flagged for you to confirm.")
    submitted = st.form_submit_button("Build checklist", type="primary")

if submitted:
    if not name.strip():
        st.warning("Give the use case a name.")
    else:
        uc = UseCase(
            name=name.strip(),
            description=description.strip(),
            sector=sector,
            team=TEAMS[team],
            lifecycle_stage=lifecycle,
            **answers,
        )
        with st.spinner(
            "Searching each stage (the first check after a restart can take ~2 minutes; later ones are instant)..."
        ):
            st.session_state.checklist = run_check(uc, cfg, system)

cl: Checklist | None = st.session_state.get("checklist")
if cl is not None:
    n = cl.counts()
    st.divider()
    st.subheader(cl.use_case.name)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 Mandatory", n["binding"])
    m2.metric("🟠 Regulator expects", n["expectation"])
    m3.metric("🟢 Recommended", n["voluntary"])
    m4.metric("Stages", len(cl.stages))
    slug = "".join(ch if ch.isalnum() else "_" for ch in cl.use_case.name.lower()).strip("_")[:60]
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("⬇ Checklist (CSV, to track status)", to_csv(cl), f"{slug}.csv", "text/csv")
    d2.download_button("⬇ Report (Markdown)", to_markdown(cl), f"{slug}.md", "text/markdown")
    st.caption(DISCLAIMER)

    st.markdown("#### Key points for this use case")
    for x in cl.notes + cl.assumptions:
        st.markdown(f"- {x}")

    current = None
    for s in cl.stages:
        if s.playbook_title != current:
            current = s.playbook_title
            st.markdown(f"### {html.escape(current)}")
        with st.expander(f"{s.stage.title} · {len(s.items)} item(s)", expanded=False):
            st.markdown(f"**Evidence typically produced:** {s.stage.evidence}")
            st.markdown(f"**Usually involves:** {', '.join(s.stage.involve)}")
            if not s.has_binding:
                msg = "No binding paragraph in this library matched this stage."
                if s.playbook_id in ("personal_info", "automated_decisions"):
                    msg += (
                        " Privacy Act obligations apply, but the Act's text is not yet live here."
                    )
                st.caption(msg)
            if s.see_also:
                refs = "; ".join(dict.fromkeys(f"{i.document} {i.citation}" for i in s.see_also))
                st.caption(f"Also relevant, listed above: {refs}")
            for i in s.items:
                flags = []
                if i.not_yet_in_force:
                    flags.append(f"⏳ from {i.effective_from}")
                if i.explains_law:
                    flags.append("⚖️ explains binding law")
                if i.weak:
                    flags.append("❔ weaker match")
                color = TIER_COLOR.get(i.tier, "#555")
                st.markdown(
                    f'<span style="background:{color};color:white;border-radius:4px;padding:1px 7px;'
                    f'font-size:0.75rem;font-weight:600">{html.escape(TIER_MARK.get(i.tier, i.tier))}</span> '
                    f"**{html.escape(i.document)} {html.escape(i.citation)}** "
                    f"<small>{html.escape(' · '.join(flags))}</small>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"> {i.excerpt}")
                if i.url:
                    st.markdown(
                        f"<small>[Source document ↗]({i.url})</small>", unsafe_allow_html=True
                    )

    if cl.gaps:
        st.markdown("#### Not covered by this library: check separately")
        for g in cl.gaps:
            st.markdown(f"- **{g.title}.** {g.note}")

st.caption(footer_text(system.index_version))
