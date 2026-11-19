"""AU AI Regulation Navigator - Streamlit UI.

Run:  make app   (or: uv run streamlit run app/streamlit_app.py)
"""

from __future__ import annotations

import html
import os
from pathlib import Path

import streamlit as st

from regnav.config import TIER_LABELS, AppConfig, Secrets, load_config
from regnav.generate.answer import AnswerResult, answer_question
from regnav.generate.llm import LLMConfig, StubClient, make_llm
from regnav.generate.schema import SECTIONS
from regnav.observability.langfuse import get_tracer
from regnav.retrieve import RetrievalSystem, build_retrieval

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {
    "Tier-stratified hybrid (recommended)": "configs/hybrid_stratified.yaml",
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
        "guidance - not itself enforceable",
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


# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Settings")
    config_label = st.selectbox("Retrieval configuration", list(CONFIGS))
    sector_label = st.selectbox("Your sector", list(SECTORS))
    offline = st.toggle(
        "Offline demo (no LLM)",
        value=os.environ.get("REGNAV_UI_OFFLINE") == "1",
        help="Uses a deterministic stub that quotes the top source of each tier - for demos without an API key.",
    )
    st.caption(
        "Answers are grouped by legal force. Binding prudential standards are technology-neutral: they "
        "rarely say 'AI', which is why naive retrieval misses them."
    )

config_path = CONFIGS[config_label]
sector = SECTORS[sector_label]

# ----------------------------------------------------------------------------- main
st.title("⚖️ AU AI Regulation Navigator")
st.markdown(
    "Ask about AI in Australian financial services. Every claim is cited and labelled as "
    f"{badge('Mandatory', TIER_COLOR['binding'])} {badge('Regulator expects', TIER_COLOR['expectation'])} "
    f"{badge('Recommended', TIER_COLOR['voluntary'])}.",
    unsafe_allow_html=True,
)

try:
    cfg, retrieval = get_system(config_path)
except FileNotFoundError as e:
    st.error(f"{e}. Build the index first: `make ingest`.")
    st.stop()

if "question" not in st.session_state:
    st.session_state.question = EXAMPLES[0]
cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES, strict=True):
    if col.button(ex, use_container_width=True):
        st.session_state.question = ex

question = st.text_area("Question", key="question", height=80)
ask = st.button("Ask", type="primary")

if ask and question.strip():
    llm = get_llm(config_path, offline)
    with st.spinner("Retrieving and generating..."):
        result: AnswerResult = answer_question(
            question.strip(),
            cfg,
            retrieval,
            llm,
            sector=sector,
            tracer=None if offline else get_cached_tracer(),
        )
    st.session_state.result = result

result: AnswerResult | None = st.session_state.get("result")
if result is not None:
    by_id = {c.chunk_id: c for c in result.retrieved}
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Answer")
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
                items.append(
                    f"<li style='margin-bottom:6px'>{html.escape(c.claim)} "
                    f"<code style='font-size:0.75rem'>{html.escape(label + para)}</code></li>"
                )
            st.markdown(
                f"<div style='border-left:5px solid {color};background:{bg};padding:10px 14px;"
                f"border-radius:6px;margin-bottom:12px;color:#101828'>"
                f"<div style='font-weight:700;color:{color}'>{title} "
                f"<span style='font-weight:400;color:#475467;font-size:0.85rem'>· {sub}</span></div>"
                f"<ul style='margin:6px 0 0 0'>{''.join(items)}</ul></div>",
                unsafe_allow_html=True,
            )
        st.caption(f"⚠️ {result.disclaimer}")
        flags = []
        if result.gate_reason:
            flags.append("scope gate")
        if result.repaired:
            flags.append("claims repaired")
        if result.fallback:
            flags.append("safe fallback")
        st.caption(
            f"config `{result.config_name}` · index `{result.index_version}` · prompt `{result.prompt_version}` · "
            f"{result.total_latency_s:.1f}s · tokens {result.input_tokens}/{result.output_tokens}"
            + (f" · {', '.join(flags)}" if flags else "")
        )
        if result.trace_url:
            st.markdown(f"[Open Langfuse trace ↗]({result.trace_url})")
        if result.error:
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
                + f"<b>{html.escape(title)}</b>"
            )
            st.markdown(head, unsafe_allow_html=True)
            with st.expander(f"#{c.rank} {c.chunk_id} · score {c.score:.3f}", expanded=False):
                body = c.text.split("\n", 1)[-1]
                st.markdown(f"**{m.get('doc_title', '')}**  \nSection: {m.get('section', '')}")
                if m.get("effective_from"):
                    st.markdown(f"Effective from: `{m['effective_from']}`")
                st.text(body)
                if m.get("url"):
                    st.markdown(f"[Source document ↗]({m['url']})")
