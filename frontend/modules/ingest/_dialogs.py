"""Rename and edit-source dialogs."""
import streamlit as st

from ..api_client import api_get, api_patch, api_put


@st.dialog("Rename context")
def rename_dialog(ctx_id: str, current_name: str, t: dict) -> None:
    new_name = st.text_input(
        t["ctx_name_placeholder"],
        value=current_name,
        label_visibility="collapsed",
        placeholder=t["ctx_name_placeholder"],
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t["ctx_save"], use_container_width=True, type="primary"):
            if new_name.strip():
                try:
                    api_patch(f"/contexts/{ctx_id}", {"name": new_name.strip()})
                    active = st.session_state.get("active_context")
                    if active and active.get("context_id") == ctx_id:
                        active["name"] = new_name.strip()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    with col2:
        if st.button(t["ctx_cancel"], use_container_width=True):
            st.rerun()


@st.dialog("Edit source")
def edit_source_dialog(ctx_id: str, doc_id: str, t: dict) -> None:
    try:
        raw = api_get(f"/contexts/{ctx_id}/sources/{doc_id}/text")
    except Exception as e:
        st.error(t["error_prefix"].format(e))
        return
    new_title = st.text_input(t["label_text_title"], value=raw.get("title", ""))
    new_text  = st.text_area(t["label_text_area"],  value=raw.get("raw_text", ""), height=400)
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t["ctx_save"], use_container_width=True, type="primary"):
            try:
                api_put(f"/contexts/{ctx_id}/sources/{doc_id}", {"text": new_text, "title": new_title})
                st.rerun()
            except Exception as e:
                st.error(t["error_prefix"].format(e))
    with col2:
        if st.button(t["ctx_cancel"], use_container_width=True):
            st.rerun()
