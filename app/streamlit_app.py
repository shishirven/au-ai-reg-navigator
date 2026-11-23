"""AU AI Regulation Navigator - Streamlit entry point and navigation.

Run:  make app   (or: uv run streamlit run app/streamlit_app.py)

Pages (app/views/): Home (objective, how to use, the document library), Model-use check, Ask a
question. Logging, page settings and the optional demo password are handled here once for all pages.
"""

from __future__ import annotations

import os
import sys

import streamlit as st

from regnav.logging_utils import setup_logging

# Cloud Run keeps stdout. INFO so an LLM failure is visible next to the request log.
if os.environ.get("REGNAV_PUBLIC_DEMO") == "1" or os.environ.get("K_SERVICE"):
    setup_logging("INFO", stream=sys.stdout)

from regnav.demo_guard import footer_text, password_ok, password_required

st.set_page_config(page_title="AU AI Regulation Navigator", page_icon="⚖️", layout="wide")

if password_required() and not st.session_state.get("demo_authed"):
    st.title("⚖️ AU AI Regulation Navigator")
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

nav = st.navigation(
    [
        st.Page("views/home.py", title="Home", icon="🏠", default=True),
        st.Page("views/model_use_check.py", title="Model-use check", icon="🧭"),
        st.Page("views/ask.py", title="Ask a question", icon="💬"),
    ]
)
nav.run()
