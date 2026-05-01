"""Sources list and history accordions."""
import streamlit as st

from ..api_client import api_get, api_delete
from ._dialogs import edit_source_dialog

_HISTORY_ICONS: dict[str, str] = {
    "source_added":   "➕",
    "source_edited":  "✏️",
    "source_deleted": "🗑️",
}


def sources_accordion(t: dict, ctx_id: str) -> None:
    try:
        sources = api_get(f"/contexts/{ctx_id}/sources")
    except Exception:
        sources = []

    with st.expander(f"{t['ctx_sources_section']} ({len(sources)})", expanded=False):
        if not sources:
            st.caption(t["ctx_sources_empty"])
            return
        for src in sources:
            doc_id = src.get("document_id", "")
            title  = src.get("title") or doc_id[:8]
            s_type = src.get("source_type", "")
            col_info, col_edit_btn, col_del_btn = st.columns([5, 1, 1])
            with col_info:
                st.markdown(f"**{title}**")
                st.caption(s_type)
            with col_edit_btn:
                if st.button("✏️", key=f"src_edit_{doc_id}", help=t["ctx_edit_source"]):
                    edit_source_dialog(ctx_id, doc_id, t)
            with col_del_btn:
                if st.button("🗑️", key=f"src_del_{doc_id}", help=t["ctx_delete_source"]):
                    try:
                        api_delete(f"/contexts/{ctx_id}/sources/{doc_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(t["error_prefix"].format(e))


def history_accordion(t: dict, ctx_id: str) -> None:
    with st.expander(t["ctx_history_section"], expanded=False):
        try:
            entries = api_get(f"/contexts/{ctx_id}/history")
        except Exception:
            entries = []
        if not entries:
            st.caption(t["ctx_history_empty"])
            return
        for entry in entries[:30]:
            ts     = entry.get("timestamp", "")[:16].replace("T", " ")
            action = entry.get("action", "")
            detail = entry.get("detail", "")
            icon   = _HISTORY_ICONS.get(action, "•")
            st.markdown(f"{icon} `{ts}` {detail}")
