import streamlit as st

from .api_client import api_get, api_put, api_delete
from .chat import chat_content
from .sidebar import sidebar_content


def _sources_tab(T: dict[str, str], context_id: str) -> None:
    try:
        sources = api_get(f"/contexts/{context_id}/sources")
    except Exception as e:
        st.error(T["error_prefix"].format(e))
        return

    if not sources:
        st.info(T["ctx_sources_empty"])
        return

    for src in sources:
        doc_id = src.get("document_id", "")
        title = src.get("title") or doc_id
        source_type = src.get("source_type", "")
        chunk_count = src.get("chunk_count", 0)
        ingested_at = src.get("ingested_at", "")[:10]

        with st.container(border=True):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(f"**{title}**")
                st.caption(f"{T['ctx_source_type']}: {source_type} · {chunk_count} {T['ctx_chunks']} · {ingested_at}")
            with col_del:
                if st.button(
                    T["ctx_delete_source"],
                    key=f"delsrc_{doc_id}",
                    use_container_width=True,
                ):
                    try:
                        api_delete(f"/contexts/{context_id}/sources/{doc_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(T["error_prefix"].format(e))

            with st.expander(T["ctx_edit_source"]):
                try:
                    raw = api_get(f"/contexts/{context_id}/sources/{doc_id}/text")
                    edit_title = st.text_input(
                        T["label_text_title"],
                        value=raw.get("title", title),
                        key=f"edit_title_{doc_id}",
                    )
                    edit_text = st.text_area(
                        T["label_text_area"],
                        value=raw.get("raw_text", ""),
                        height=250,
                        key=f"edit_text_{doc_id}",
                    )
                    if st.button(T["ctx_save_source"], key=f"save_{doc_id}"):
                        try:
                            api_put(
                                f"/contexts/{context_id}/sources/{doc_id}",
                                {"text": edit_text, "title": edit_title},
                            )
                            st.success(T["status_done"])
                            st.rerun()
                        except Exception as e:
                            st.error(T["error_prefix"].format(e))
                except Exception as e:
                    st.error(T["error_prefix"].format(e))


def _history_tab(T: dict[str, str], context_id: str) -> None:
    try:
        entries = api_get(f"/contexts/{context_id}/history")
    except Exception as e:
        st.error(T["error_prefix"].format(e))
        return

    if not entries:
        st.info(T["ctx_history_empty"])
        return

    for entry in entries:
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        action = entry.get("action", "")
        detail = entry.get("detail", "")
        st.markdown(f"`{ts}` **{action}** — {detail}")


def context_view(T: dict[str, str], lang: str, ctx: dict) -> None:
    if st.button(T["ctx_back"]):
        st.session_state.active_context = None
        st.rerun()

    st.title(ctx["name"])

    tab_chat, tab_sources, tab_history = st.tabs([
        T["ctx_tab_chat"],
        T["ctx_tab_sources"],
        T["ctx_tab_history"],
    ])

    with tab_chat:
        with st.sidebar:
            sidebar_content(T, lang, context_id=ctx["context_id"])
        chat_content(T, context_id=ctx["context_id"])

    with tab_sources:
        _sources_tab(T, ctx["context_id"])

    with tab_history:
        _history_tab(T, ctx["context_id"])
