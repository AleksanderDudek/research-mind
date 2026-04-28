"""Chat UI package — public surface is chat_content and _run_question."""
import streamlit as st

from ..api_client import api_post
from ._history import render_history, render_sources
from ._state import load_messages, persist_message, scroll_to_bottom

_SKELETON_HTML = """
<div class="skeleton" style="width:80%"></div>
<div class="skeleton" style="width:60%"></div>
<div class="skeleton" style="width:70%"></div>
"""

_PENDING_KEY = "_pending_question"


def _run_question(t: dict[str, str], context_id: str | None, prompt: str) -> None:
    user_msg: dict = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_msg)
    if context_id:
        st.session_state[_PENDING_KEY] = {"question": prompt, "context_id": context_id}

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        skeleton = st.empty()
        skeleton.markdown(_SKELETON_HTML, unsafe_allow_html=True)
        with st.spinner(t["spinner_agent"]):
            try:
                res    = api_post("/query/ask", {"question": prompt, "context_id": context_id})
                answer = res["answer"]
                st.session_state.pop(_PENDING_KEY, None)
                skeleton.empty()
                st.markdown(answer)
                sources = res.get("sources", [])
                if sources:
                    render_sources(t, sources)
                asst_msg: dict = {
                    "role":         "assistant",
                    "content":      answer,
                    "sources":      sources,
                    "action_taken": res["action_taken"],
                    "iterations":   res["iterations"],
                    "critique":     res.get("critique"),
                }
                st.session_state.messages.append(asst_msg)
                if context_id:
                    persist_message(context_id, user_msg)
                    persist_message(context_id, asst_msg)
            except Exception as e:
                st.session_state.pop(_PENDING_KEY, None)
                skeleton.empty()
                st.error(t["error_prefix"].format(e))


def _check_pending(t: dict[str, str], context_id: str | None) -> None:
    pending = st.session_state.get(_PENDING_KEY)
    if not pending:
        return
    if context_id and pending.get("context_id") != context_id:
        return
    st.warning(f"**{t['pending_banner']}**  \n> {pending['question']}")
    col_resume, col_dismiss = st.columns(2)
    with col_resume:
        if st.button(t["pending_resume"], type="primary", use_container_width=True):
            st.session_state.pop(_PENDING_KEY)
            _run_question(t, context_id, pending["question"])
    with col_dismiss:
        if st.button(t["pending_dismiss"], use_container_width=True):
            st.session_state.pop(_PENDING_KEY)
            st.rerun()


def chat_content(t: dict[str, str], context_id: str | None = None) -> None:
    if context_id:
        load_messages(context_id)

    _check_pending(t, context_id)
    render_history(t)

    if st.session_state.pop("_scroll_to_bottom", False):
        scroll_to_bottom()

    from ..voice import inject_voice_fab

    voice_on = st.session_state.get("_voice_conv_active", False)

    with st.container(key="rm-voice-on"):
        if st.button("▶", key="_rm_voice_on_btn"):
            st.session_state["_voice_conv_active"] = True
            st.rerun()
    with st.container(key="rm-voice-off"):
        if st.button("⏹", key="_rm_voice_off_btn"):
            st.session_state["_voice_conv_active"] = False
            st.rerun()

    if voice_on:
        st.markdown('<div id="rm-voice-active" style="display:none"></div>',
                    unsafe_allow_html=True)
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown(
                '<div class="rm-voice-circle" id="rm-voice-circle-main"></div>',
                unsafe_allow_html=True,
            )

    inject_voice_fab()

    if prompt := st.chat_input(t["chat_placeholder"]):
        _run_question(t, context_id, prompt)
