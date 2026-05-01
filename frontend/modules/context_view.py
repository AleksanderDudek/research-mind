import html as _html
import streamlit as st

from .chat import chat_content
from .ingest import (
    rename_dialog,
    tab_pdf_url, tab_web, tab_upload, tab_text, tab_image, tab_audio,
    sources_accordion, history_accordion,
)

_SOURCE_KEYS  = ["tab_pdf_url", "tab_web", "tab_upload", "tab_text", "tab_image", "tab_audio"]
_SOURCE_ICONS = ["📄", "🌐", "📎", "📝", "🖼️", "🎵"]
_SOURCE_FNS   = [tab_pdf_url, tab_web, tab_upload, tab_text, tab_image, tab_audio]


def _context_header(t: dict, ctx: dict) -> None:
    ctx_id = ctx["context_id"]
    name   = _html.escape(ctx["name"])
    col_back, col_title, col_edit = st.columns([2, 7, 1])
    with col_back:
        if st.button(t["ctx_back"], key="btn_back", use_container_width=True):
            st.session_state.active_context = None
            st.session_state.messages = []
            st.session_state.pop("editing_context_name", None)
            st.rerun()
    with col_title:
        st.markdown(f'<div class="rm-ctx-title">{name}</div>', unsafe_allow_html=True)
    with col_edit:
        if st.button("✏️", key="btn_rename_ctx", use_container_width=True, help=t["ctx_rename"]):
            rename_dialog(ctx_id, ctx["name"], t)
    st.divider()


def _sources_tab(t: dict, ctx_id: str) -> None:
    if msg := st.session_state.pop("_ingest_ok", None):
        st.success(msg)

    options  = [f"{icon} {t[key]}" for icon, key in zip(_SOURCE_ICONS, _SOURCE_KEYS)]
    selected = st.pills(
        "source_type", options=options,
        selection_mode="single", default=options[0],
        label_visibility="collapsed",
    )
    n = st.session_state.get("_ingest_n", 0)
    if selected:
        _SOURCE_FNS[options.index(selected)](t, ctx_id, n)

    st.divider()
    sources_accordion(t, ctx_id)
    history_accordion(t, ctx_id)


def context_view(t: dict, ctx: dict) -> None:
    ctx_id = ctx["context_id"]
    _context_header(t, ctx)
    tab_chat, tab_sources = st.tabs([
        "💬 " + t["ctx_tab_chat"],
        "📥 " + t["ctx_tab_sources"],
    ])
    with tab_chat:
        chat_content(t, context_id=ctx_id)
    with tab_sources:
        _sources_tab(t, ctx_id)
