import streamlit as st
import streamlit.components.v1 as components

from modules.chat import chat_content
from modules.i18n import get_lang, get_T
from modules.sidebar import sidebar_content
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

# ── Styles ─────────────────────────────────────────────────────────────────────

inject_styles()

# ── Layout ─────────────────────────────────────────────────────────────────────

with st.sidebar:
    sidebar_content(T, lang)

chat_content(T)
