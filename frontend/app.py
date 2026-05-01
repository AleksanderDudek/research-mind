import streamlit as st

from modules.context_panel import context_panel
from modules.context_view import context_view
from modules.i18n import get_lang, get_translations
from modules.styles import inject_styles

st.set_page_config(page_title="ResearchMind", page_icon="📚", layout="centered")

inject_styles()

lang = get_lang()
T    = get_translations(lang)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_context" not in st.session_state:
    st.session_state.active_context = None

if st.session_state.active_context is None:
    context_panel(T)
else:
    context_view(T, st.session_state.active_context)
