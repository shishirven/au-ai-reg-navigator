"""Model-use check (D-053): a guided flow for data, AI and analytics teams.

Start -> about your model -> a few one-tap questions -> review -> an interactive checklist the team
works through (status, owner, evidence) and exports. Layout follows the "task list" service pattern
(question pages, check your answers, task list with statuses). No language model is called: every
checklist item quotes its source paragraph.
"""

from __future__ import annotations

import html
import os
import threading
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

from regnav.assess import UseCase, run_check, warm_up
from regnav.assess.checklist import Checklist, ChecklistItem
from regnav.assess.render import DISCLAIMER, STATUSES, to_csv, to_markdown
from regnav.config import load_config
from regnav.demo_guard import footer_text, public_demo_enabled
from regnav.retrieve import build_retrieval

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/hybrid_stratified_rerank.yaml"

EXAMPLES = [
    ("📈", "Motor pricing model", "Actuarial · insurer · cloud ML platform", "motor_pricing_gbm"),
    (
        "💬",
        "Complaints summariser",
        "Data science · bank · LLM API, offshore",
        "genai_complaints_assistant",
    ),
    (
        "🎯",
        "Churn propensity model",
        "Analytics · bank · built in-house",
        "churn_propensity_internal",
    ),
]
SECTORS = {"Bank": "bank", "Insurer": "insurer"}
TEAMS = {
    "Data science / ML": "data_science",
    "Actuarial": "actuarial",
    "Analytics / BI": "analytics",
    "Data engineering": "data_engineering",
    "Other": "other",
}
STAGES = {
    "Idea": "idea",
    "Build": "build",
    "Validate": "validate",
    "Deploy": "deploy",
    "Live": "live",
}
ANSWERS = {"Yes": "yes", "No": "no", "Not sure": "unsure"}
LABEL = {v: k for k, v in ANSWERS.items()}

# One question per screen. `show` decides whether a follow-up applies.
QUESTIONS: list[dict[str, Any]] = [
    {
        "key": "personal_information",
        "chip": "Personal information",
        "title": "Does it use personal information?",
        "hint": "Anything about an identifiable person, in training data, inputs, prompts or outputs.",
        "icon": "👤",
    },
    {
        "key": "sensitive_information",
        "chip": "Sensitive information",
        "title": "Any sensitive information?",
        "hint": "Health, biometric, racial or ethnic origin, criminal record and similar categories.",
        "icon": "🩺",
        "show": lambda a: a.get("personal_information") in ("yes", "unsure"),
    },
    {
        "key": "decisions_about_individuals",
        "chip": "Decisions about people",
        "title": "Does it make, or strongly influence, decisions about people?",
        "hint": "Pricing, underwriting, credit, claims, eligibility, offers. Include it if a person "
        "decides but relies heavily on the model's output.",
        "icon": "⚖️",
    },
    {
        "key": "generative_ai",
        "chip": "Generative AI",
        "title": "Does it use generative AI or an LLM?",
        "hint": "For example a chatbot, a summariser, a coding assistant or a model API such as an LLM.",
        "icon": "✨",
    },
    {
        "key": "third_party",
        "chip": "Vendor / API / platform",
        "title": "Does it rely on an outside vendor, model API or platform?",
        "hint": "A bought model, a hosted model API, or a cloud ML platform run by someone else.",
        "icon": "🤝",
    },
    {
        "key": "offshore",
        "chip": "Offshore",
        "title": "Are any data, models or support staff outside Australia?",
        "hint": "Include where the vendor hosts your data or runs the model.",
        "icon": "🌏",
        "show": lambda a: a.get("third_party") in ("yes", "unsure"),
    },
    {
        "key": "critical_operation",
        "chip": "Critical operation",
        "title": "Would an outage disrupt a critical operation?",
        "hint": "For example claims, payments or pricing at scale: something customers or the "
        "business can't do without.",
        "icon": "🚨",
    },
]
TIER = {
    "binding": ("Mandatory", "#d92d20", "law: a binding standard"),
    "expectation": ("Regulator expects", "#dc6803", "regulator guidance"),
    "voluntary": ("Recommended", "#079455", "voluntary guidance"),
}

st.markdown(
    """
<style>
.block-container {max-width: 1080px; padding-top: 2.2rem;}
.mc-steps {display:flex; gap:.5rem; margin:.2rem 0 1.4rem 0; flex-wrap:wrap;}
.mc-step {display:flex; align-items:center; gap:.45rem; padding:.35rem .8rem; border-radius:999px;
  font-size:.85rem; border:1px solid rgba(128,128,128,.25); opacity:.55;}
.mc-step b {display:inline-flex; width:1.35rem; height:1.35rem; border-radius:50%; align-items:center;
  justify-content:center; font-size:.75rem; background:rgba(128,128,128,.2);}
.mc-step.on {opacity:1; border-color:#2e90fa; background:rgba(46,144,250,.10);}
.mc-step.on b {background:#2e90fa; color:white;}
.mc-step.done {opacity:.9;} .mc-step.done b {background:#079455; color:white;}
.mc-hero {font-size:2.1rem; font-weight:750; line-height:1.2; margin:0 0 .4rem 0;}
.mc-sub {font-size:1.05rem; opacity:.8; margin-bottom:1.2rem;}
.mc-card {border:1px solid rgba(128,128,128,.22); border-radius:14px; padding:1rem 1.1rem;
  background:rgba(128,128,128,.04); height:100%;}
.mc-card h4 {margin:.1rem 0 .3rem 0; font-size:1rem;}
.mc-card p {margin:0; font-size:.88rem; opacity:.8;}
.mc-q {font-size:1.7rem; font-weight:700; line-height:1.25; margin:.4rem 0 .4rem 0;}
.mc-hint {opacity:.75; font-size:1rem; margin-bottom:1.3rem;}
.mc-icon {font-size:2.2rem;}
.mc-tag {display:inline-block; padding:.08rem .55rem; border-radius:999px; font-size:.75rem;
  font-weight:650; color:white; white-space:nowrap;}
.mc-soft {display:inline-block; padding:.05rem .5rem; border-radius:999px; font-size:.75rem;
  border:1px solid rgba(128,128,128,.35); opacity:.85; margin-left:.25rem; white-space:nowrap;}
.mc-quote {border-left:3px solid rgba(128,128,128,.35); padding:.15rem 0 .15rem .8rem;
  margin:.45rem 0 .6rem 0; font-size:.93rem; opacity:.92;}
.mc-key {border-radius:12px; padding:.7rem .95rem; margin-bottom:.5rem; font-size:.94rem;
  border:1px solid rgba(46,144,250,.35); background:rgba(46,144,250,.08);}
.mc-key.warn {border-color:rgba(220,104,3,.45); background:rgba(220,104,3,.08);}
.mc-meta {font-size:.85rem; opacity:.75; margin:.1rem 0 .6rem 0;}
.mc-row {display:flex; justify-content:space-between; align-items:center; gap:1rem;}
.mc-big {font-size:1.9rem; font-weight:750; line-height:1;}
.mc-small {font-size:.8rem; opacity:.75;}
</style>
""",
    unsafe_allow_html=True,
)

demo = public_demo_enabled()


@st.cache_resource(show_spinner="Loading the regulation library...")
def get_system(config_path: str):
    os.chdir(ROOT)
    cfg = load_config(config_path)
    return cfg, build_retrieval(cfg)


@st.cache_resource(show_spinner=False)
def start_warm_up(config_path: str) -> threading.Thread:
    """Search every stage in the background once per process, so checklists appear quickly."""
    cfg, system = get_system(config_path)
    t = threading.Thread(target=warm_up, args=(cfg, system), daemon=True)
    t.start()
    return t


config_path = (os.environ.get("REGNAV_CONFIG") or "configs/prod.yaml") if demo else DEFAULT_CONFIG
try:
    cfg, system = get_system(config_path)
except FileNotFoundError as e:
    st.error(f"{e}. Build the index first: `make ingest`.")
    st.stop()
start_warm_up(config_path)

ss = st.session_state
ss.setdefault("mc_step", "start")  # start | about | ask | review | result
ss.setdefault("mc_q", 0)
ss.setdefault("mc_a", {})
ss.setdefault("mc_track", {})


# ----------------------------------------------------------------------------- helpers
def go(step: str, q: int = 0) -> None:
    ss.mc_step, ss.mc_q = step, q


def visible_questions() -> list[dict[str, Any]]:
    return [q for q in QUESTIONS if q.get("show", lambda a: True)(ss.mc_a)]


def expected_total() -> int:
    """Questions still to come count until they are ruled out, so the total only ever shrinks."""
    parents = {"sensitive_information": "personal_information", "offshore": "third_party"}
    n = 0
    for q in QUESTIONS:
        parent = parents.get(q["key"])
        if parent is None or ss.mc_a.get(parent) in (None, "yes", "unsure"):
            n += 1
    return n


def answer(key: str, value: str) -> None:
    ss.mc_a[key] = value
    for q in QUESTIONS:  # drop answers to follow-ups that no longer apply
        if "show" in q and not q["show"](ss.mc_a):
            ss.mc_a.pop(q["key"], None)
    qs = visible_questions()
    idx = next(i for i, q in enumerate(qs) if q["key"] == key)
    if ss.get("mc_return_to_review"):
        missing = [q for q in qs if q["key"] not in ss.mc_a]
        if not missing:
            ss.mc_return_to_review = False
            go("review")
            return
        go("ask", qs.index(missing[0]))
        return
    go("ask", idx + 1) if idx + 1 < len(qs) else go("review")


def load_example(stem: str) -> None:
    uc = UseCase.from_yaml(ROOT / "data" / "use_cases" / f"{stem}.yaml")
    ss.mc_a = uc.model_dump()
    for q in QUESTIONS:
        if "show" in q and not q["show"](ss.mc_a):
            ss.mc_a.pop(q["key"], None)
    go("review")


def start_fresh() -> None:
    ss.mc_a = {"sector": "bank", "team": "data_science", "lifecycle_stage": "build"}
    go("about")


def restart() -> None:
    for k in ("mc_a", "mc_track", "mc_cl"):
        ss.pop(k, None)
    ss.mc_a, ss.mc_track = {}, {}
    go("start")


def steps_bar(active: int) -> None:
    names = ["Describe your model", "Review", "Your checklist"]
    parts = []
    for i, n in enumerate(names, 1):
        cls = "on" if i == active else ("done" if i < active else "")
        mark = "✓" if i < active else str(i)
        parts.append(f'<div class="mc-step {cls}"><b>{mark}</b>{n}</div>')
    st.markdown(f'<div class="mc-steps">{"".join(parts)}</div>', unsafe_allow_html=True)


def keep_open(stage_id: str) -> None:
    ss.mc_open = stage_id  # keep the section being worked on open across reruns


def tag(tier: str) -> str:
    label, color, _ = TIER[tier]
    return f'<span class="mc-tag" style="background:{color}">{label}</span>'


def to_use_case() -> UseCase:
    a = {k: v for k, v in ss.mc_a.items() if k in UseCase.model_fields}
    for q in QUESTIONS:  # skipped follow-ups count as "no" (they don't apply)
        a.setdefault(q["key"], "no")
    a["name"] = (a.get("name") or "My model").strip()
    return UseCase.model_validate(a)


# ----------------------------------------------------------------------------- 0. start
if ss.mc_step == "start":
    st.markdown(
        '<div class="mc-hero">Which rules apply to your model?</div>'
        '<div class="mc-sub">For data scientists, actuaries and analytics teams at banks and '
        "insurers. Answer a few quick questions and get a checklist of the requirements to "
        "check, quoted from APRA standards, regulator guidance and privacy guidance, grouped by "
        "stage of the model lifecycle. About two minutes. Take it to your risk partner.</div>",
        unsafe_allow_html=True,
    )
    steps_bar(1)
    c1, c2, c3 = st.columns(3)
    for col, (icon, title, text) in zip(
        (c1, c2, c3),
        [
            ("🧭", "1 · Describe", "Name the model, then 6–8 yes / no / not sure questions."),
            (
                "🔎",
                "2 · We search",
                "Each lifecycle stage is checked against the regulation library.",
            ),
            ("✅", "3 · Work through it", "Mark items met / not met, add owners, export to CSV."),
        ],
        strict=True,
    ):
        col.markdown(
            f'<div class="mc-card"><div class="mc-icon">{icon}</div><h4>{title}</h4><p>{text}</p></div>',
            unsafe_allow_html=True,
        )
    st.write("")
    st.button("Start with my model  →", type="primary", on_click=start_fresh)
    st.markdown("##### Or open an example")
    cols = st.columns(3)
    for col, (icon, title, sub, stem) in zip(cols, EXAMPLES, strict=True):
        with col:
            st.markdown(
                f'<div class="mc-card"><div class="mc-icon">{icon}</div><h4>{title}</h4><p>{sub}</p></div>',
                unsafe_allow_html=True,
            )
            st.button(
                "Open example",
                key=f"ex_{stem}",
                on_click=load_example,
                args=(stem,),
                use_container_width=True,
            )
    st.caption(
        "A starting point for the conversation with risk, compliance and privacy, not legal advice "
        "and not a compliance verdict. No AI model writes the checklist: every item quotes its source."
    )

# ----------------------------------------------------------------------------- 1a. about
elif ss.mc_step == "about":
    steps_bar(1)
    st.progress(0.05, text="About your model")
    st.markdown('<div class="mc-q">Tell us about the model</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="mc-hint">A name is enough. The description helps you and your reviewers later.</div>',
        unsafe_allow_html=True,
    )
    a = ss.mc_a
    name = st.text_input(
        "Model or use case name", a.get("name", ""), placeholder="e.g. Home loan pre-approval model"
    )
    desc = st.text_area(
        "What it does, for whom (optional)",
        a.get("description", ""),
        height=80,
        placeholder="e.g. Scores applications and suggests pre-approval; a lender makes the final call.",
    )
    c1, c2 = st.columns(2)
    with c1:
        sector = st.segmented_control(
            "Your organisation",
            list(SECTORS),
            default=next(k for k, v in SECTORS.items() if v == a.get("sector", "bank")),
        )
        stage = st.segmented_control(
            "Where is it in its life?",
            list(STAGES),
            default=next(k for k, v in STAGES.items() if v == a.get("lifecycle_stage", "build")),
        )
    with c2:
        team = st.pills(
            "Your team",
            list(TEAMS),
            default=next(k for k, v in TEAMS.items() if v == a.get("team", "data_science")),
        )
    b1, b2, _ = st.columns([1, 1, 4])
    b1.button("← Back", on_click=go, args=("start",), use_container_width=True)
    if b2.button("Continue →", type="primary", use_container_width=True, disabled=not name.strip()):
        a.update(
            name=name.strip(),
            description=desc.strip(),
            sector=SECTORS[sector or "Bank"],
            team=TEAMS[team or "Data science / ML"],
            lifecycle_stage=STAGES[stage or "Build"],
        )
        go("ask", 0)
        st.rerun()

# ----------------------------------------------------------------------------- 1b. questions
elif ss.mc_step == "ask":
    steps_bar(1)
    qs = visible_questions()
    i = min(ss.mc_q, len(qs) - 1)
    q = qs[i]
    total = expected_total()
    st.progress((i + 1) / (total + 1), text=f"Question {i + 1} of {total}")
    st.markdown(
        f'<div class="mc-icon">{q["icon"]}</div><div class="mc-q">{html.escape(q["title"])}</div>'
        f'<div class="mc-hint">{html.escape(q["hint"])}</div>',
        unsafe_allow_html=True,
    )
    current = ss.mc_a.get(q["key"])
    cols = st.columns([1, 1, 1, 2])
    for col, (label, value) in zip(cols, ANSWERS.items(), strict=False):
        col.button(
            label,
            key=f"ans_{q['key']}_{value}",
            on_click=answer,
            args=(q["key"], value),
            type="primary" if current == value else "secondary",
            use_container_width=True,
        )
    st.caption("Not sure? That's fine: the item is included and flagged for you to confirm.")
    st.write("")
    back = ("ask", i - 1) if i > 0 else ("about", 0)
    st.button("← Back", on_click=go, args=back)

# ----------------------------------------------------------------------------- 2. review
elif ss.mc_step == "review":
    steps_bar(2)
    a = ss.mc_a
    st.markdown('<div class="mc-q">Check your answers</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="mc-hint">Change anything that isn\'t right, then build your checklist.</div>',
        unsafe_allow_html=True,
    )

    def edit_about() -> None:
        go("about")

    def edit_q(key: str) -> None:
        ss.mc_return_to_review = True
        go("ask", [q["key"] for q in visible_questions()].index(key))

    rows = [
        (
            "Model",
            a.get("name", "") + (f" — {a['description']}" if a.get("description") else ""),
            edit_about,
            (),
        ),
        (
            "Organisation · team · stage",
            f"{a.get('sector', '').capitalize()} · {next((k for k, v in TEAMS.items() if v == a.get('team')), '')} · "
            f"{a.get('lifecycle_stage', '').capitalize()}",
            edit_about,
            (),
        ),
    ] + [
        (q["title"], LABEL.get(a.get(q["key"], ""), "—"), edit_q, (q["key"],))
        for q in visible_questions()
    ]
    for label, value, fn, args in rows:
        c1, c2, c3 = st.columns([3, 3, 1])
        c1.markdown(f"**{html.escape(label)}**")
        c2.markdown(html.escape(str(value)) + (" ⚠️" if value == "Not sure" else ""))
        c3.button("Change", key=f"chg_{label}", on_click=fn, args=args, type="tertiary")
    unanswered = [q for q in visible_questions() if q["key"] not in a]
    st.write("")
    b1, b2, _ = st.columns([1, 1.6, 3])
    b1.button("← Start over", on_click=restart, use_container_width=True)
    if b2.button(
        "Build my checklist →", type="primary", use_container_width=True, disabled=bool(unanswered)
    ):
        uc = to_use_case()
        with st.status(
            "Checking each stage against the regulation library...", expanded=False
        ) as s:
            ss.mc_cl = run_check(uc, cfg, system)
            s.update(label="Checklist ready", state="complete")
        ss.mc_track = {}
        go("result")
        st.rerun()
    if unanswered:
        st.caption(f"Answer {len(unanswered)} more question(s) first.")
    st.caption(
        "The first checklist after the app starts can take a minute or two while every stage is "
        "searched once; after that they are instant."
    )

# ----------------------------------------------------------------------------- 3. result
elif ss.mc_step == "result" and ss.get("mc_cl") is not None:
    cl: Checklist = ss.mc_cl
    track: dict[str, dict[str, str]] = ss.mc_track
    steps_bar(3)
    uc = cl.use_case
    items = cl.items
    # Widgets below hold the latest values; sync them first so counts and progress are current.
    for it in items:
        rec = track.setdefault(it.chunk_id, {"status": "To check", "owner": "", "evidence": ""})
        if f"st_{it.chunk_id}" in ss:
            rec["status"] = ss[f"st_{it.chunk_id}"] or "To check"
        for field, prefix in (("owner", "ow_"), ("evidence", "ev_")):
            if f"{prefix}{it.chunk_id}" in ss:
                rec[field] = ss[f"{prefix}{it.chunk_id}"]
    reviewed = sum(
        1 for i in items if track.get(i.chunk_id, {}).get("status", "To check") != "To check"
    )
    n = cl.counts()

    top_l, top_r = st.columns([3, 1.3])
    with top_l:
        st.markdown(
            f'<div class="mc-q" style="margin-top:0">{html.escape(uc.name)}</div>',
            unsafe_allow_html=True,
        )
        chips = [
            uc.sector.capitalize(),
            uc.team.replace("_", " ").capitalize(),
            uc.lifecycle_stage.capitalize(),
        ]
        chips += [q["chip"] for q in QUESTIONS if getattr(uc, q["key"]) == "yes"]
        chips += [f"{q['chip']}?" for q in QUESTIONS if getattr(uc, q["key"]) == "unsure"]
        st.markdown(
            " ".join(f'<span class="mc-soft">{html.escape(c)}</span>' for c in chips),
            unsafe_allow_html=True,
        )
    with top_r:
        st.markdown(
            f'<div class="mc-card"><div class="mc-big">{reviewed}/{len(items)}</div>'
            f'<div class="mc-small">items reviewed</div></div>',
            unsafe_allow_html=True,
        )
    st.progress(reviewed / max(1, len(items)))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 Mandatory", n["binding"], help="Binding prudential standards (law)")
    m2.metric("🟠 Regulator expects", n["expectation"], help="Regulator guidance and letters")
    m3.metric("🟢 Recommended", n["voluntary"], help="Voluntary government guidance")
    m4.metric("Lifecycle stages", len(cl.stages))

    st.markdown("#### What stands out for this model")
    for note in cl.notes[1:]:
        warn = "commences" in note or "unsure" in note.lower() or "Unsure" in note
        st.markdown(
            f'<div class="mc-key {"warn" if warn else ""}">{html.escape(note)}</div>',
            unsafe_allow_html=True,
        )
    st.caption(" ".join(([cl.notes[0]] if cl.notes else []) + cl.assumptions))

    tab_list, tab_gaps, tab_export = st.tabs(
        [f"✅ Checklist ({len(items)})", f"🧩 Not covered here ({len(cl.gaps)})", "⬇ Export"]
    )

    with tab_list:
        f1, f2 = st.columns([3, 1.4])
        show_tiers = f1.pills(
            "Show",
            ["Mandatory", "Regulator expects", "Recommended"],
            selection_mode="multi",
            default=["Mandatory", "Regulator expects", "Recommended"],
            label_visibility="collapsed",
        )
        hide_done = f2.toggle("Hide reviewed", value=False)
        wanted = {t for t, (label, _, _) in TIER.items() if label in (show_tiers or [])}

        current_pb = None
        for s in cl.stages:
            visible = [
                i
                for i in s.items
                if i.tier in wanted
                and not (
                    hide_done and track.get(i.chunk_id, {}).get("status", "To check") != "To check"
                )
            ]
            if s.playbook_title != current_pb:
                current_pb = s.playbook_title
                st.markdown(f"##### {html.escape(current_pb)}")
            done = sum(
                1
                for i in s.items
                if track.get(i.chunk_id, {}).get("status", "To check") != "To check"
            )
            total = len(s.items)
            status = "✅" if total and done == total else ("🟡" if done else "⚪")
            dots = {"binding": "🔴", "expectation": "🟠", "voluntary": "🟢"}
            counts = " ".join(
                f"{dots[t]}{sum(1 for i in s.items if i.tier == t)}"
                for t in TIER
                if any(i.tier == t for i in s.items)
            )
            with st.expander(
                expanded=ss.get("mc_open") == s.stage.id,
                label=f"{status}  {s.stage.title}  ·  {done}/{total} reviewed  ·  {counts}",
            ):
                st.markdown(
                    f'<div class="mc-meta">📎 <b>Evidence teams typically produce:</b> {html.escape(s.stage.evidence)}<br>'
                    f"👥 <b>Usually involves:</b> {html.escape(', '.join(s.stage.involve))}</div>",
                    unsafe_allow_html=True,
                )
                if not s.has_binding:
                    msg = "No binding paragraph in this library matched this stage."
                    if s.playbook_id in ("personal_info", "automated_decisions"):
                        msg += " Privacy Act obligations still apply; the Act's text isn't in the library yet."
                    st.caption(msg)
                if s.see_also:
                    refs = "; ".join(
                        dict.fromkeys(f"{i.document} {i.citation}" for i in s.see_also)
                    )
                    st.caption(f"Also relevant, listed in an earlier stage: {refs}")
                if not visible and s.items:
                    st.caption("All items here are filtered out or reviewed.")
                for it in visible:
                    it: ChecklistItem
                    flags = []
                    if it.not_yet_in_force:
                        flags.append(f'<span class="mc-soft">⏳ from {it.effective_from}</span>')
                    if it.explains_law:
                        flags.append('<span class="mc-soft">⚖️ explains binding law</span>')
                    if it.weak:
                        flags.append('<span class="mc-soft">❔ weaker match</span>')
                    cite = f"<b>{html.escape(it.document)} {html.escape(it.citation)}</b>"
                    if it.url:
                        cite = (
                            f'<a href="{html.escape(it.url)}" target="_blank" rel="noopener" '
                            f'title="Open the source at this passage">{cite}&nbsp;↗</a>'
                        )
                    st.markdown(
                        f"{tag(it.tier)} {cite} {''.join(flags)}"
                        f'<div class="mc-quote">{html.escape(it.excerpt)}</div>',
                        unsafe_allow_html=True,
                    )
                    rec = track.setdefault(
                        it.chunk_id, {"status": "To check", "owner": "", "evidence": ""}
                    )
                    c1, c2, c3 = st.columns([2.2, 1.2, 1.6])
                    new = c1.segmented_control(
                        "Status",
                        STATUSES,
                        default=rec["status"],
                        key=f"st_{it.chunk_id}",
                        on_change=keep_open,
                        args=(s.stage.id,),
                        label_visibility="collapsed",
                    )
                    rec["status"] = new or "To check"
                    rec["owner"] = c2.text_input(
                        "Owner",
                        rec["owner"],
                        key=f"ow_{it.chunk_id}",
                        on_change=keep_open,
                        args=(s.stage.id,),
                        placeholder="Owner",
                        label_visibility="collapsed",
                    )
                    rec["evidence"] = c3.text_input(
                        "Evidence",
                        rec["evidence"],
                        key=f"ev_{it.chunk_id}",
                        on_change=keep_open,
                        args=(s.stage.id,),
                        placeholder="Evidence link or note",
                        label_visibility="collapsed",
                    )
                    st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)

    with tab_gaps:
        st.markdown(
            "These may also apply to your model but **aren't in this library**. Check them with your "
            "legal, compliance or privacy team."
        )
        for g in cl.gaps:
            st.markdown(f"- **{html.escape(g.title)}.** {html.escape(g.note)}")

    with tab_export:
        slug = (
            "".join(ch if ch.isalnum() else "_" for ch in uc.name.lower()).strip("_")[:60]
            or "model"
        )
        st.markdown(
            "Your statuses, owners and evidence are included. Attach the report to your risk "
            "assessment or model inventory entry; keep tracking in the CSV."
        )
        e1, e2, _ = st.columns([1, 1, 2])
        e1.download_button(
            "⬇ Checklist (CSV)",
            to_csv(cl, track),
            f"{slug}_checklist.csv",
            "text/csv",
            use_container_width=True,
            type="primary",
        )
        e2.download_button(
            "⬇ Report (Markdown)",
            to_markdown(cl, track),
            f"{slug}_report.md",
            "text/markdown",
            use_container_width=True,
        )
        st.caption(
            f"Generated {cl.generated.isoformat()} · config `{cl.config_name}` · index `{cl.index_version}`"
        )

    st.divider()
    b1, b2, _ = st.columns([1, 1.4, 2.6])
    b1.button("✏️ Edit answers", on_click=go, args=("review",), use_container_width=True)
    b2.button("↺ Check another model", on_click=restart, use_container_width=True)
    st.caption(
        f"⚠️ {DISCLAIMER} Statuses are kept for this browser session only: export to keep them."
    )

else:
    go("start")
    st.rerun()

st.caption(footer_text(system.index_version) + f" · {date.today().isoformat()}")
