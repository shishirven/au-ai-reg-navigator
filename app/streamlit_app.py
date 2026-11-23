"""AU AI Regulation Navigator - Streamlit UI.

Run:  make app   (or: uv run streamlit run app/streamlit_app.py)
"""

from __future__ import annotations

import html
import os
import sys
from pathlib import Path

import streamlit as st

from regnav.logging_utils import setup_logging

# Cloud Run keeps stdout. INFO so an LLM failure is visible next to the request log.
if os.environ.get("REGNAV_PUBLIC_DEMO") == "1" or os.environ.get("K_SERVICE"):
    setup_logging("INFO", stream=sys.stdout)

from regnav.authority import note_for
from regnav.config import TIER_LABELS, AppConfig, Secrets, load_config
from regnav.coverage import gaps_for_question
from regnav.demo_guard import (
    banner_text,
    footer_text,
    force_offline,
    max_questions_per_session,
    password_ok,
    password_required,
    public_demo_enabled,
    question_block_reason,
)
from regnav.generate.answer import AnswerResult, answer_question
from regnav.generate.llm import FallbackClient, LLMConfig, StubClient, make_llm
from regnav.generate.schema import SECTIONS
from regnav.observability.langfuse import get_tracer
from regnav.retrieve import RetrievalSystem, build_retrieval

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {
    "Tier-stratified + re-ranking (recommended)": "configs/hybrid_stratified_rerank.yaml",
    "Re-ranking + per-document cap (candidate, D-052)": "configs/hybrid_stratified_capped.yaml",
    "Tier-stratified hybrid": "configs/hybrid_stratified.yaml",
    "Hybrid pooled (dense + BM25)": "configs/hybrid_pooled.yaml",
    "Dense pooled (naive baseline)": "configs/baseline_dense.yaml",
    "Tier-stratified, local Ollama": "configs/local_stratified.yaml",
}
SECTORS = {
    "Bank (ADI)": "bank",
    "Insurer": "insurer",
    "Superannuation (RSE licensee)": "super",
    "Any business": "any_business",
}
EXAMPLES = [
    "What do we need to do before engaging a third-party AI vendor?",
    "When does the APP 1.7-1.9 automated decision-making transparency obligation commence?",
    "What governance arrangements does APRA expect for AI at a minimum?",
    "Should we tell customers when they are interacting with AI?",
]
SECTION_STYLE = {
    "mandatory": ("Mandatory", "binding standard - legally enforceable", "#b42318", "#fef3f2"),
    "regulator_expects": (
        "Regulator expects",
        "regulator guidance - the document itself is not law; see any ⚖️ note below",
        "#b54708",
        "#fffaeb",
    ),
    "recommended": ("Recommended", "voluntary guidance", "#027a48", "#ecfdf3"),
}
TIER_COLOR = {"binding": "#b42318", "expectation": "#b54708", "voluntary": "#027a48"}

st.set_page_config(page_title="AU AI Regulation Navigator", page_icon="⚖️", layout="wide")


def badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:white;border-radius:4px;padding:1px 7px;'
        f'font-size:0.75rem;font-weight:600;white-space:nowrap">{html.escape(text)}</span>'
    )


@st.cache_resource(show_spinner="Loading index and embedding model...")
def get_system(config_path: str) -> tuple[AppConfig, RetrievalSystem]:
    os.chdir(ROOT)
    cfg = load_config(config_path)
    return cfg, build_retrieval(cfg)


@st.cache_resource
def get_llm(config_path: str, offline: bool):
    cfg = load_config(ROOT / config_path)
    if offline:
        return StubClient(LLMConfig(provider="stub", model="offline-stub"))
    return make_llm(cfg.generation, cfg.seed, Secrets().anthropic_api_key)


@st.cache_resource
def get_cached_tracer():
    return get_tracer(Secrets())


demo = public_demo_enabled()

# ----------------------------------------------------------------------------- main, before the index loads
st.title("⚖️ AU AI Regulation Navigator")
if demo:
    st.warning(banner_text(langfuse_enabled=Secrets().langfuse_enabled))

if password_required() and not st.session_state.get("demo_authed"):
    with st.form("demo_login"):
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Continue")
    if submitted:
        if password_ok(pw):
            st.session_state.demo_authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.caption(footer_text("not loaded"))
    st.stop()

# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    if demo:
        config_path = os.environ.get("REGNAV_CONFIG") or "configs/prod.yaml"
        st.caption(f"Retrieval configuration is locked to `{config_path}`.")
    else:
        config_label = st.selectbox("Retrieval configuration", list(CONFIGS))
        config_path = CONFIGS[config_label]
    sector_label = st.selectbox("Your sector", list(SECTORS))
    ui_offline = os.environ.get("REGNAV_UI_OFFLINE") == "1"
    if demo and force_offline(ui_offline=False):
        offline = True
        st.info(
            "GROQ_API_KEY is not set, so this demo is in offline mode. "
            "Answers come from a deterministic stub, not the Groq model."
        )
    else:
        offline = st.toggle(
            "Offline demo (no LLM)",
            value=ui_offline,
            help="Uses a deterministic stub that quotes the top source of each tier - for demos without an API key.",
        )
        offline = force_offline(ui_offline=offline)
    st.caption(
        "Answers are grouped by legal force. Binding prudential standards are technology-neutral: they "
        "rarely say 'AI', which is why naive retrieval misses them."
    )

sector = SECTORS[sector_label]


def model_status_html(llm) -> str:
    """Which model will answer the next question: API, local fallback, or offline stub."""
    if isinstance(llm, StubClient):
        return badge("OFFLINE DEMO", "#475467") + " deterministic stub, no LLM"
    if isinstance(llm, FallbackClient):
        st_ = llm.status()
        if st_["fallback_active"]:
            local = "ollama" in st_["fallback"]
            label = "💻 LOCAL" if local else "FALLBACK"
            return (
                badge(label, "#b54708") + f" {html.escape(st_['fallback'])}<br>"
                f"<span style='font-size:0.8rem'>{html.escape(st_['reason'])}</span>"
            )
        return (
            badge("🌐 API", "#155eef") + f" {html.escape(st_['primary'])}<br>"
            f"<span style='font-size:0.8rem'>fallback if limited: {html.escape(st_['fallback'])}</span>"
        )
    where = "💻 LOCAL" if llm.cfg.provider == "ollama" else "🌐 API"
    return (
        badge(where, "#b54708" if where.endswith("LOCAL") else "#155eef")
        + f" {html.escape(llm.cfg.provider)} · {html.escape(llm.cfg.model)}"
    )


with st.sidebar:
    st.subheader("Model status")
    status_slot = st.empty()  # filled at the end of the run, after any fallback has happened

st.markdown(
    "For data leads, data scientists, actuaries and analytics teams at banks and insurers. "
    "Ask about AI and model use under Australian regulation; for a checklist on one model, use "
    "**Model-use check** in the sidebar. Every claim is cited and labelled as "
    f"{badge('Mandatory', TIER_COLOR['binding'])} {badge('Regulator expects', TIER_COLOR['expectation'])} "
    f"{badge('Recommended', TIER_COLOR['voluntary'])}.",
    unsafe_allow_html=True,
)

try:
    cfg, retrieval = get_system(config_path)
except FileNotFoundError as e:
    st.error(f"{e}. Build the index first: `make ingest`.")
    st.caption(footer_text("not built"))
    st.stop()

if "question" not in st.session_state:
    st.session_state.question = EXAMPLES[0]
cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES, strict=True):
    if col.button(ex, use_container_width=True):
        st.session_state.question = ex

question = st.text_area("Question", key="question", height=80)
ask = st.button("Ask", type="primary")
blocked = None
if ask and question.strip() and demo:
    blocked = question_block_reason(question, st.session_state.get("questions_asked", 0))
    if blocked:
        st.warning(blocked)

if ask and question.strip() and not blocked:
    if demo:
        st.session_state.questions_asked = st.session_state.get("questions_asked", 0) + 1
    llm = get_llm(config_path, offline)
    local = (
        isinstance(llm, FallbackClient) and llm.status()["fallback_active"]
    ) or llm.cfg.provider == "ollama"
    spinner = (
        "Generating with the local model on this machine - this can take 1-3 minutes on CPU..."
        if local
        else "Retrieving and generating..."
    )
    with st.spinner(spinner):
        result: AnswerResult = answer_question(
            question.strip(),
            cfg,
            retrieval,
            llm,
            sector=sector,
            tracer=None if offline else get_cached_tracer(),
        )
    st.session_state.result = result

if demo:
    st.caption(
        f"Public demo: {max_questions_per_session()} questions per session, "
        f"500 characters each. Used {st.session_state.get('questions_asked', 0)}."
    )

result: AnswerResult | None = st.session_state.get("result")
if result is not None:
    by_id = {c.chunk_id: c for c in result.retrieved}
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Answer")
        if result.llm_provider:
            is_local = result.llm_provider == "ollama"
            label = "💻 Local model" if is_local else "🌐 API model"
            color = "#b54708" if is_local else "#155eef"
            if result.llm_provider == "stub":
                label, color = "Offline demo stub", "#475467"
            elif result.llm_fallback_reason and not is_local:
                label, color = "Fallback model", "#b54708"
            text = f"{badge(label, color)} <code>{html.escape(result.llm_provider)} · {html.escape(result.llm_model)}</code>"
            if result.llm_fallback_reason:
                note = (
                    "Answers from the smaller local model can be less complete."
                    if is_local
                    else "This answer is from the fallback model, not Groq."
                )
                text += (
                    f"<div style='background:#fffaeb;border:1px solid #fedf89;border-radius:6px;padding:6px 10px;"
                    f"margin-top:6px;color:#93370d;font-size:0.85rem'>⚠️ Fallback in use: "
                    f"{html.escape(result.llm_fallback_reason)}. {note}</div>"
                )
            st.markdown(text, unsafe_allow_html=True)
        elif result.gate_reason:
            st.markdown(
                badge("No model call", "#475467") + " answered by the scope gate",
                unsafe_allow_html=True,
            )
        if result.answer.abstained:
            st.warning(f"**No answer given.** {result.answer.abstain_reason}")
        for section in SECTIONS:
            claims = getattr(result.answer, section)
            if not claims:
                continue
            title, sub, color, bg = SECTION_STYLE[section]
            items = []
            for c in claims:
                src = by_id.get(c.citation_id)
                label = src.metadata.get("short_name", "?") if src else "?"
                para = f" para {src.metadata['para']}" if src and src.metadata.get("para") else ""
                note = note_for(str(src.metadata.get("doc_id", ""))) if src else None
                note_html = (
                    f"<div style='font-size:0.8rem;color:#6941c6;margin-top:2px'>⚖️ {html.escape(note.badge)}</div>"
                    if note and section != "mandatory"
                    else ""
                )
                items.append(
                    f"<li style='margin-bottom:6px'>{html.escape(c.claim)} "
                    f"<code style='font-size:0.75rem'>{html.escape(label + para)}</code>{note_html}</li>"
                )
            st.markdown(
                f"<div style='border-left:5px solid {color};background:{bg};padding:10px 14px;"
                f"border-radius:6px;margin-bottom:12px;color:#101828'>"
                f"<div style='font-weight:700;color:{color}'>{title} "
                f"<span style='font-weight:400;color:#475467;font-size:0.85rem'>· {sub}</span></div>"
                f"<ul style='margin:6px 0 0 0'>{''.join(items)}</ul></div>",
                unsafe_allow_html=True,
            )
        gaps = gaps_for_question(result.question)
        if gaps:
            st.markdown(
                "**Not covered by this library: check separately.** "
                + " ".join(f"*{html.escape(g.title)}*: {html.escape(g.note)}" for g in gaps)
            )
        st.caption(f"⚠️ {result.disclaimer}")
        flags = []
        if result.gate_reason:
            flags.append("scope gate")
        if result.repaired:
            flags.append("claims repaired")
        if result.fallback:
            flags.append("safe abstention")
        st.caption(
            f"config `{result.config_name}` · index `{result.index_version}` · prompt `{result.prompt_version}` · "
            f"{result.total_latency_s:.1f}s · tokens {result.input_tokens}/{result.output_tokens}"
            + (f" · {', '.join(flags)}" if flags else "")
        )
        if result.trace_url:
            st.markdown(f"[Open Langfuse trace ↗]({result.trace_url})")
        if result.error:
            if demo:
                st.error("The language model is unavailable right now. No answer was generated.")
            else:
                st.error(result.error)

    with right:
        st.subheader("Sources")
        cited = {cid for _, _, cid in result.cited()}
        for c in result.retrieved:
            m = c.metadata
            title = f"{m.get('short_name', '')}" + (f" · para {m['para']}" if m.get("para") else "")
            head = (
                f"{badge(TIER_LABELS.get(c.tier, c.tier), TIER_COLOR.get(c.tier, '#475467'))} "
                f"{badge(c.modality, '#475467')} "
                + (badge("cited", "#155eef") + " " if c.chunk_id in cited else "")
                + (
                    badge("⚖️ explains binding law", "#6941c6") + " "
                    if note_for(str(m.get("doc_id", "")))
                    else ""
                )
                + f"<b>{html.escape(title)}</b>"
            )
            st.markdown(head, unsafe_allow_html=True)
            with st.expander(f"#{c.rank} {c.chunk_id} · score {c.score:.3f}", expanded=False):
                body = c.text.split("\n", 1)[-1]
                st.markdown(f"**{m.get('doc_title', '')}**  \nSection: {m.get('section', '')}")
                if m.get("effective_from"):
                    st.markdown(f"Effective from: `{m['effective_from']}`")
                if note := note_for(str(m.get("doc_id", ""))):
                    st.info(f"⚖️ {note.note}")
                st.text(body)
                if m.get("url"):
                    st.markdown(f"[Source document ↗]({m['url']})")

# Model status reflects the state *after* this run (e.g. a fallback that just opened).
status_slot.markdown(model_status_html(get_llm(config_path, offline)), unsafe_allow_html=True)
if demo:
    answered = ""
    if result is not None and result.llm_model:
        answered = f" · answered by {result.llm_provider} {result.llm_model}"
        if result.llm_fallback_reason:
            answered += " (fallback)"
    st.caption(footer_text(retrieval.index_version) + answered)
