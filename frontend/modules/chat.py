import streamlit as st

from .api_client import api_post

_SKELETON_HTML = """
<div class="skeleton" style="width:80%"></div>
<div class="skeleton" style="width:60%"></div>
<div class="skeleton" style="width:70%"></div>
"""


def _render_sources(T: dict[str, str], sources: list[dict]) -> None:
    with st.expander(T["sources_label"].format(len(sources))):
        for i, src in enumerate(sources, 1):
            st.markdown(
                f"**[{i}]** `{src.get('source', 'unknown')}` "
                f"(score: {src.get('score', 0):.3f})"
            )
            st.text(str(src.get("text", ""))[:500] + "...")


def _render_history(T: dict[str, str]) -> None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                _render_sources(T, msg["sources"])


@st.fragment
def chat_content(T: dict[str, str]) -> None:
    st.title(T["app_title"])
    st.caption(T["app_caption"])

    _render_history(T)

    if prompt := st.chat_input(T["chat_placeholder"]):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            skeleton = st.empty()
            skeleton.markdown(_SKELETON_HTML, unsafe_allow_html=True)

            with st.spinner(T["spinner_agent"]):
                try:
                    res = api_post("/query/ask", {"question": prompt})
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
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    })
                except Exception as e:
                    skeleton.empty()
                    st.error(T["error_prefix"].format(e))
