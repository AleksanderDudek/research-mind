import streamlit as st

from .chat import chat_content
from .sidebar import context_sidebar


def context_view(t: dict, ctx: dict) -> None:
    with st.sidebar:
        context_sidebar(t, ctx)
    chat_content(t, context_id=ctx["context_id"])
