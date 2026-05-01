"""Message loading, persistence and scroll helpers."""
import streamlit as st
import streamlit.components.v1 as _components

from ..api_client import api_get, api_post


def scroll_to_bottom() -> None:
    _components.html(
        "<script>window.parent.scrollTo("
        "{top: window.parent.document.body.scrollHeight, behavior: 'smooth'}"
        ");</script>",
        height=0,
    )


def load_messages(context_id: str) -> None:
    """Fetch messages from the backend; no-op if already loaded for this context."""
    if st.session_state.get("_chat_ctx") == context_id:
        return
    try:
        st.session_state.messages = api_get(f"/contexts/{context_id}/messages")
    except Exception:
        st.session_state.messages = []
    st.session_state["_chat_ctx"] = context_id
    if st.session_state.messages:
        st.session_state["_scroll_to_bottom"] = True


def persist_message(context_id: str, msg: dict) -> None:
    try:
        api_post(f"/contexts/{context_id}/messages", {
            "role":         msg["role"],
            "content":      msg["content"],
            "sources":      msg.get("sources"),
            "action_taken": msg.get("action_taken"),
            "iterations":   msg.get("iterations"),
            "critique":     msg.get("critique"),
        })
    except Exception:
        pass
