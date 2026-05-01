"""Chat message rendering: sources, pairs, history paging."""
import base64

import streamlit as st

_VISIBLE_PAIRS = 10


def render_sources(t: dict[str, str], sources: list[dict]) -> None:
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


def render_pair(
    t: dict[str, str],
    user_msg: dict,
    asst_msg: dict,
    show_sources: bool,
) -> None:
    with st.chat_message("user"):
        st.markdown(user_msg["content"])
    with st.chat_message("assistant"):
        st.markdown(asst_msg["content"])
        sources = asst_msg.get("sources") or []
        if show_sources and sources:
            render_sources(t, sources)
        elif sources:
            st.caption(f"📚 {t['sources_label'].format(len(sources))}")
        action     = asst_msg.get("action_taken")
        iterations = asst_msg.get("iterations")
        critique   = (asst_msg.get("critique") or {}).get("score")
        if action or iterations:
            with st.expander("Details", expanded=False):
                st.caption(t["action_label"].format(
                    action or "—", iterations or "—", critique or "?",
                ))


def render_history(t: dict[str, str]) -> None:
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

    older  = pairs[:-_VISIBLE_PAIRS] if len(pairs) > _VISIBLE_PAIRS else []
    recent = pairs[-_VISIBLE_PAIRS:]  if len(pairs) > _VISIBLE_PAIRS else pairs

    if older:
        with st.expander(t["chat_earlier"].format(len(older)), expanded=False):
            for u, a in older:
                render_pair(t, u, a, show_sources=False)

    for u, a in recent:
        render_pair(t, u, a, show_sources=True)
