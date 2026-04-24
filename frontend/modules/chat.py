import base64

import streamlit as st

from .api_client import api_get, api_post

_SKELETON_HTML = """
<div class="skeleton" style="width:80%"></div>
<div class="skeleton" style="width:60%"></div>
<div class="skeleton" style="width:70%"></div>
"""

_VISIBLE_PAIRS = 10


def _render_sources(T: dict[str, str], sources: list[dict]) -> None:
    with st.expander(T["sources_label"].format(len(sources))):
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


def _render_pair(T: dict[str, str], user_msg: dict, asst_msg: dict, show_sources: bool) -> None:
    with st.chat_message("user"):
        st.markdown(user_msg["content"])
    with st.chat_message("assistant"):
        st.markdown(asst_msg["content"])
        st.caption(T["action_label"].format(
            asst_msg.get("action_taken", "—"),
            asst_msg.get("iterations", "—"),
            (asst_msg.get("critique") or {}).get("score", "?"),
        ))
        if show_sources and asst_msg.get("sources"):
            _render_sources(T, asst_msg["sources"])
        elif not show_sources:
            n = len(asst_msg.get("sources") or [])
            if n:
                st.caption(f"📎 {T['sources_label'].format(n)}")


def _render_history(T: dict[str, str]) -> None:
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
        with st.expander(T["chat_earlier"].format(len(older)), expanded=False):
            for user_msg, asst_msg in older:
                _render_pair(T, user_msg, asst_msg, show_sources=False)

    for user_msg, asst_msg in recent:
        _render_pair(T, user_msg, asst_msg, show_sources=True)


def _load_messages(context_id: str) -> None:
    """Fetch persisted messages from backend when entering a context."""
    if st.session_state.get("_chat_ctx") == context_id:
        return
    try:
        st.session_state.messages = api_get(f"/contexts/{context_id}/messages")
    except Exception:
        st.session_state.messages = []
    st.session_state["_chat_ctx"] = context_id


def _persist_message(context_id: str, msg: dict) -> None:
    """Save one message to the backend; silently ignore failures."""
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


def chat_content(T: dict[str, str], context_id: str | None = None) -> None:
    if context_id:
        _load_messages(context_id)

    st.title(T["app_title"])
    st.caption(T["app_caption"])

    _render_history(T)

    if prompt := st.chat_input(T["chat_placeholder"]):
        user_msg: dict = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_msg)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            skeleton = st.empty()
            skeleton.markdown(_SKELETON_HTML, unsafe_allow_html=True)

            with st.spinner(T["spinner_agent"]):
                try:
                    res = api_post("/query/ask", {"question": prompt, "context_id": context_id})
                    answer = res["answer"]
                    skeleton.empty()
                    st.markdown(answer)
                    st.caption(T["action_label"].format(
                        res["action_taken"],
                        res["iterations"],
                        res.get("critique", {}).get("score", "?"),
                    ))
                    sources = res.get("sources", [])
                    if sources:
                        _render_sources(T, sources)
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
                    skeleton.empty()
                    st.error(T["error_prefix"].format(e))
