import streamlit as st

from modules.context_panel import context_panel
from modules.context_view import context_view
from modules.i18n import get_lang, get_translations
from modules.sidebar import panel_sidebar
from modules.styles import inject_styles

# Must be the absolute first Streamlit command
st.set_page_config(page_title="ResearchMind", page_icon="📚", layout="wide")

# ── Language ───────────────────────────────────────────────────────────────────

lang = get_lang()
T = get_translations(lang)


# ── Session state ──────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_context" not in st.session_state:
    st.session_state.active_context = None

# ── Styles ─────────────────────────────────────────────────────────────────────

inject_styles()

# ── Layout ─────────────────────────────────────────────────────────────────────

if st.session_state.active_context is None:
    with st.sidebar:
        panel_sidebar(T)
    context_panel(T)
else:
    context_view(T, st.session_state.active_context)
