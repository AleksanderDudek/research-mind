import base64

import streamlit as st

from .api_client import api_get, api_post

_SKELETON_HTML = """
<div class="skeleton" style="width:80%"></div>
<div class="skeleton" style="width:60%"></div>
<div class="skeleton" style="width:70%"></div>
"""

_VISIBLE_PAIRS = 10
_PENDING_KEY = "_pending_question"


def _render_sources(t: dict[str, str], sources: list[dict]) -> None:
    with st.expander(t["sources_label"].format(len(sources))):
        for i, src in enumerate(sources, 1):
            st.markdown(
                f"**[{i}]** `{src.get('source', 'unknown')}` "
                f"(score: {src.get('score', 0):.3f})"
            )
            if src.get("source_type") == "image" and src.get("image_data"):
                st.image(
                    base64.b64decode(src["image_data"]),
                    caption=src.get("source", ""),
                    use_container_width=True,
                )
            else:
                st.text(str(src.get("text", ""))[:500] + "...")


def _render_pair(t: dict[str, str], user_msg: dict, asst_msg: dict, show_sources: bool) -> None:
    with st.chat_message("user"):
        st.markdown(user_msg["content"])
    with st.chat_message("assistant"):
        st.markdown(asst_msg["content"])
        sources = asst_msg.get("sources") or []
        if show_sources and sources:
            _render_sources(t, sources)
        elif sources:
            st.caption(f"📚 {t['sources_label'].format(len(sources))}")
        # Technical metadata tucked away for power users
        action = asst_msg.get("action_taken")
        iterations = asst_msg.get("iterations")
        critique = (asst_msg.get("critique") or {}).get("score")
        if action or iterations:
            with st.expander("Details", expanded=False):
                st.caption(t["action_label"].format(action or "—", iterations or "—", critique or "?"))


def _render_history(t: dict[str, str]) -> None:
    msgs = st.session_state.messages
    if not msgs:
        return

    pairs: list[tuple[dict, dict]] = []
    i = 0
    while i + 1 < len(msgs):
        if msgs[i]["role"] == "user" and msgs[i + 1]["role"] == "assistant":
            pairs.append((msgs[i], msgs[i + 1]))
            i += 2
        else:
            i += 1

    older = pairs[:-_VISIBLE_PAIRS] if len(pairs) > _VISIBLE_PAIRS else []
    recent = pairs[-_VISIBLE_PAIRS:] if len(pairs) > _VISIBLE_PAIRS else pairs

    if older:
        with st.expander(t["chat_earlier"].format(len(older)), expanded=False):
            for user_msg, asst_msg in older:
                _render_pair(t, user_msg, asst_msg, show_sources=False)

    for user_msg, asst_msg in recent:
        _render_pair(t, user_msg, asst_msg, show_sources=True)


def _load_messages(context_id: str) -> None:
    if st.session_state.get("_chat_ctx") == context_id:
        return
    try:
        st.session_state.messages = api_get(f"/contexts/{context_id}/messages")
    except Exception:
        st.session_state.messages = []
    st.session_state["_chat_ctx"] = context_id


def _persist_message(context_id: str, msg: dict) -> None:
    try:
        api_post(f"/contexts/{context_id}/messages", {
            "role": msg["role"],
            "content": msg["content"],
            "sources": msg.get("sources"),
            "action_taken": msg.get("action_taken"),
            "iterations": msg.get("iterations"),
            "critique": msg.get("critique"),
        })
    except Exception:
        pass


def _run_question(t: dict[str, str], context_id: str | None, prompt: str) -> None:
    user_msg: dict = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_msg)

    # Save pending state BEFORE the blocking call so navigation away is recoverable
    if context_id:
        st.session_state[_PENDING_KEY] = {"question": prompt, "context_id": context_id}

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        skeleton = st.empty()
        skeleton.markdown(_SKELETON_HTML, unsafe_allow_html=True)

        with st.spinner(t["spinner_agent"]):
            try:
                res = api_post("/query/ask", {"question": prompt, "context_id": context_id})
                st.session_state.pop(_PENDING_KEY, None)
                answer = res["answer"]
                skeleton.empty()
                st.markdown(answer)
                sources = res.get("sources", [])
                if sources:
                    _render_sources(t, sources)
                asst_msg: dict = {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "action_taken": res["action_taken"],
                    "iterations": res["iterations"],
                    "critique": res.get("critique"),
                }
                st.session_state.messages.append(asst_msg)
                if context_id:
                    _persist_message(context_id, user_msg)
                    _persist_message(context_id, asst_msg)
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
    col_resume, col_dismiss = st.columns([1, 1])
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
        _load_messages(context_id)

    _check_pending(t, context_id)
    _render_history(t)

    if prompt := st.chat_input(t["chat_placeholder"]):
        _run_question(t, context_id, prompt)
