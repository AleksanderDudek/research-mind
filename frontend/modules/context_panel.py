import streamlit as st

from .api_client import api_get, api_post, api_delete
from .sidebar import _rename_dialog


def context_panel(T: dict[str, str]) -> None:
    col_title, col_create = st.columns([3, 2])
    with col_title:
        st.title(T["ctx_panel_title"])
    with col_create:
        st.write("")  # vertical align
        new_name = st.text_input(
            "",
            placeholder=T["ctx_name_placeholder"],
            label_visibility="collapsed",
            key="new_ctx_name",
        )
        if st.button(T["ctx_new"], use_container_width=True):
            try:
                api_post("/contexts", {"name": new_name or None})
                st.rerun()
            except Exception as e:
                st.error(T["error_prefix"].format(e))

    with st.spinner(T["ctx_loading"]):
        try:
            contexts = api_get("/contexts")
        except Exception as e:
            st.error(T["error_prefix"].format(e))
            return

    if not contexts:
        st.info(T["ctx_no_contexts"])
        return

    contexts_sorted = sorted(contexts, key=lambda c: c.get("created_at", ""), reverse=True)
    for ctx in contexts_sorted:
        with st.container(border=True):
            col_info, col_ren, col_open, col_del = st.columns([4, 1, 1, 1])
            with col_info:
                st.markdown(f"**{ctx['name']}**")
                created = ctx.get("created_at", "")[:10]
                st.caption(created)
            with col_ren:
                if st.button("✏️", key=f"ren_{ctx['context_id']}", help=T["ctx_rename"]):
                    _rename_dialog(ctx["context_id"], ctx["name"], T)
            with col_open:
                if st.button(T["ctx_open"], key=f"open_{ctx['context_id']}", use_container_width=True):
                    st.session_state.active_context = ctx
                    if "messages" in st.session_state:
                        del st.session_state["messages"]
                    st.rerun()
            with col_del:
                if st.button(T["ctx_delete"], key=f"del_{ctx['context_id']}", use_container_width=True):
                    try:
                        api_delete(f"/contexts/{ctx['context_id']}")
                        st.rerun()
                    except Exception as e:
                        st.error(T["error_prefix"].format(e))
