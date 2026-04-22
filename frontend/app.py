import streamlit as st
import streamlit.components.v1 as components

from modules.context_panel import context_panel
from modules.context_view import context_view
from modules.i18n import get_lang, get_T
from modules.styles import inject_styles

# Must be the absolute first Streamlit command
st.set_page_config(page_title="ResearchMind", page_icon="📚", layout="wide")

# ── Language ───────────────────────────────────────────────────────────────────

lang = get_lang()
T = get_T(lang)

# Redirect on first visit if ?lang is absent
components.html("""
<script>
    const params = new URLSearchParams(window.parent.location.search);
    if (!params.has('lang')) {
        const detected = (navigator.language || 'en').toLowerCase();
        params.set('lang', detected.startsWith('pl') ? 'pl' : 'en');
        window.parent.location.search = params.toString();
    }
</script>
""", height=0)

# ── Session state ──────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_context" not in st.session_state:
    st.session_state.active_context = None

# ── Styles ─────────────────────────────────────────────────────────────────────

inject_styles()

# ── Layout ─────────────────────────────────────────────────────────────────────

if st.session_state.active_context is None:
    context_panel(T)
else:
    context_view(T, lang, st.session_state.active_context)
