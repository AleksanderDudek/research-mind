import html as _html
import streamlit as st

from .api_client import api_get, api_post, api_delete
from .sidebar import _rename_dialog


def _render_delete_confirm(t: dict, ctx: dict, del_key: str) -> None:
    ctx_id = ctx["context_id"]
    st.warning(f"{t['ctx_confirm_delete']}: **{ctx['name']}**")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button(t["ctx_delete"], key=f"yes_del_{ctx_id}", type="primary", use_container_width=True):
            try:
                api_delete(f"/contexts/{ctx_id}")
            except Exception as e:
                st.error(t["error_prefix"].format(e))
            st.session_state.pop(del_key)
            st.rerun()
    with col_no:
        if st.button(t["ctx_cancel"], key=f"no_del_{ctx_id}", use_container_width=True):
            st.session_state.pop(del_key)
            st.rerun()


def _render_card(t: dict, ctx: dict) -> None:
    ctx_id = ctx["context_id"]
    del_key = f"_confirm_del_{ctx_id}"

    if st.session_state.get(del_key):
        _render_delete_confirm(t, ctx, del_key)
        st.markdown('<div class="rm-sep"></div>', unsafe_allow_html=True)
        return

    date = ctx.get("created_at", "")[:10]
    col_name, col_ren, col_del = st.columns([6, 1, 1])
    with col_name:
        st.markdown(f"**{ctx['name']}**  \n{date}")
    with col_ren:
        if st.button("✏️", key=f"ren_{ctx_id}", use_container_width=True, help=t["ctx_rename"]):
            _rename_dialog(ctx_id, ctx["name"], t)
    with col_del:
        if st.button("🗑️", key=f"del_{ctx_id}", use_container_width=True, help=t["ctx_delete"]):
            st.session_state[del_key] = True
            st.rerun()

    if st.button(t["ctx_open"] + " →", key=f"open_{ctx_id}", use_container_width=True, type="primary"):
        st.session_state.active_context = ctx
        st.session_state.pop("messages", None)
        st.rerun()

    st.markdown('<div class="rm-sep"></div>', unsafe_allow_html=True)


def context_panel(t: dict) -> None:
    lang_href = f"?lang={t['lang_toggle_target']}"
    lang_text = _html.escape(t["lang_toggle"])
    st.markdown(
        f'<div class="rm-header">'
        f'<span class="rm-header-title">📚 ResearchMind</span>'
        f'<span class="rm-header-lang"><a href="{lang_href}" target="_self">{lang_text}</a></span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption(t["app_caption"])
    st.divider()

    new_name = st.text_input(
        t["ctx_name_placeholder"],
        placeholder=t["ctx_name_placeholder"],
        label_visibility="collapsed",
        key="new_ctx_name",
    )
    if st.button(t["ctx_new"], use_container_width=True, type="primary"):
        try:
            api_post("/contexts", {"name": new_name.strip() or None})
            st.rerun()
        except Exception as e:
            st.error(t["error_prefix"].format(e))

    with st.spinner(t["ctx_loading"]):
        try:
            contexts = api_get("/contexts")
        except Exception as e:
            st.error(t["error_prefix"].format(e))
            return

    if not contexts:
        st.info(t["ctx_no_contexts"])
        return

    for ctx in sorted(contexts, key=lambda c: c.get("created_at", ""), reverse=True):
        _render_card(t, ctx)
