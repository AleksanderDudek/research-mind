"""Chat UI package — chat_content and _run_question (non-blocking with Stop)."""
import concurrent.futures
import time

import streamlit as st

from ..api_client import api_post
from ._history import render_history, render_sources
from ._state import load_messages, persist_message, scroll_to_bottom

_SKELETON_HTML = """
<div class="skeleton" style="width:80%"></div>
<div class="skeleton" style="width:60%"></div>
<div class="skeleton" style="width:70%"></div>
"""

_PENDING_KEY    = "_pending_question"
_FUTURE_KEY     = "_agent_future"
_FUTURE_PROMPT  = "_agent_prompt"
_FUTURE_CTX     = "_agent_ctx"
_FUTURE_USERMSG = "_agent_user_msg"


# ── Background request helpers ────────────────────────────────────────────────

def _start_agent(prompt: str, context_id: str | None) -> None:
    """Launch /query/ask in a background thread and store the future."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future   = executor.submit(api_post, "/query/ask",
                               {"question": prompt, "context_id": context_id})
    st.session_state[_FUTURE_KEY]     = future
    st.session_state[_FUTURE_PROMPT]  = prompt
    st.session_state[_FUTURE_CTX]     = context_id


def _cancel_agent() -> None:
    """Discard in-flight request and remove pending user message."""
    msgs = st.session_state.get("messages", [])
    user_prompt = st.session_state.get(_FUTURE_PROMPT, "")
    # Remove the dangling user message that has no assistant pair yet
    if msgs and msgs[-1]["role"] == "user" and msgs[-1]["content"] == user_prompt:
        msgs.pop()
    for k in (_FUTURE_KEY, _FUTURE_PROMPT, _FUTURE_CTX, _FUTURE_USERMSG, _PENDING_KEY):
        st.session_state.pop(k, None)


# ── Main question handler ─────────────────────────────────────────────────────

def _run_question(t: dict[str, str], context_id: str | None, prompt: str) -> None:
    """Submit prompt to the agent.  Non-blocking — uses a background thread
    and st.rerun() polling so the user can click ⏹ Stop at any time."""
    msgs = st.session_state.messages

    # ── First call: start background thread ───────────────────────────────
    if _FUTURE_KEY not in st.session_state:
        user_msg: dict = {"role": "user", "content": prompt}
        msgs.append(user_msg)
        st.session_state[_FUTURE_USERMSG] = user_msg
        if context_id:
            st.session_state[_PENDING_KEY] = {"question": prompt, "context_id": context_id}
        _start_agent(prompt, context_id)

    future  = st.session_state[_FUTURE_KEY]
    prompt_ = st.session_state[_FUTURE_PROMPT]
    ctx_    = st.session_state[_FUTURE_CTX]

    # ── Show user bubble (the pair has no assistant yet → not in history) ─
    with st.chat_message("user"):
        st.markdown(prompt_)

    # ── Show thinking state + Stop button ─────────────────────────────────
    with st.chat_message("assistant"):
        skeleton = st.empty()
        skeleton.markdown(_SKELETON_HTML, unsafe_allow_html=True)

        col_info, col_stop = st.columns([6, 1])
        with col_info:
            st.caption(t["spinner_agent"])
        with col_stop:
            if st.button("⏹", key="stop_agent_btn", help="Stop"):
                _cancel_agent()
                skeleton.empty()
                st.rerun()
                return

    # ── Poll until done ───────────────────────────────────────────────────
    if not future.done():
        time.sleep(0.25)
        st.rerun()
        return

    # ── Request finished — render answer ──────────────────────────────────
    user_msg = st.session_state.pop(_FUTURE_USERMSG, {"role": "user", "content": prompt_})
    _cancel_agent()   # clears all keys

    skeleton.empty()
    with st.chat_message("assistant"):
        try:
            res    = future.result()
            answer = res["answer"]
            st.session_state.pop(_PENDING_KEY, None)
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
            msgs.append(asst_msg)
            if ctx_:
                persist_message(ctx_, user_msg)
                persist_message(ctx_, asst_msg)
        except Exception as e:
            st.session_state.pop(_PENDING_KEY, None)
            st.error(t["error_prefix"].format(e))


def _check_pending(t: dict[str, str], context_id: str | None) -> None:
    pending = st.session_state.get(_PENDING_KEY)
    if not pending or _FUTURE_KEY in st.session_state:
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

    # While agent is running: resume the polling loop, skip the chat input
    if _FUTURE_KEY in st.session_state:
        _run_question(t, context_id, st.session_state[_FUTURE_PROMPT])
        return

    if prompt := st.chat_input(t["chat_placeholder"]):
        _run_question(t, context_id, prompt)
