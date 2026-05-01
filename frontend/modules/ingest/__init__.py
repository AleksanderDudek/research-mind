"""Ingest UI package — public surface used by context_view and context_panel."""
import streamlit as st

from ._accordions import history_accordion, sources_accordion
from ._dialogs import edit_source_dialog, rename_dialog
from ._tabs import tab_audio, tab_image, tab_pdf_url, tab_text, tab_upload, tab_web

# Kept here because it's used by both context_panel and context_view
def lang_toggle(t: dict) -> None:
    st.markdown(
        f'<a href="?lang={t["lang_toggle_target"]}" target="_self">{t["lang_toggle"]}</a>',
        unsafe_allow_html=True,
    )


__all__ = [
    "lang_toggle",
    "rename_dialog",
    "edit_source_dialog",
    "tab_pdf_url", "tab_web", "tab_upload", "tab_text", "tab_image", "tab_audio",
    "sources_accordion",
    "history_accordion",
]
