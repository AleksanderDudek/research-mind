import streamlit as st

from .api_client import api_get, api_post, api_post_audio, api_put, api_patch, api_delete


# ── Dialogs (module-level required by Streamlit) ────────────────────────────────

@st.dialog("Rename context")
def _rename_dialog(ctx_id: str, current_name: str, t: dict) -> None:
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
def _edit_source_dialog(ctx_id: str, doc_id: str, t: dict) -> None:
    try:
        raw = api_get(f"/contexts/{ctx_id}/sources/{doc_id}/text")
    except Exception as e:
        st.error(t["error_prefix"].format(e))
        return
    new_title = st.text_input(t["label_text_title"], value=raw.get("title", ""))
    new_text = st.text_area(t["label_text_area"], value=raw.get("raw_text", ""), height=400)
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


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _lang_toggle(t: dict) -> None:
    st.markdown(
        f'<a href="?lang={t["lang_toggle_target"]}" target="_self">{t["lang_toggle"]}</a>',
        unsafe_allow_html=True,
    )


def _ingest_with_feedback(t: dict, fn, *args, **kwargs) -> bool:
    with st.spinner(t["status_sending"]):
        try:
            res = fn(*args, **kwargs)
            st.session_state["_ingest_ok"] = t["ctx_ingest_success"].format(res["chunks_ingested"])
            return True
        except Exception as e:
            st.error(t["error_prefix"].format(e))
            return False


# ── Ingest tab helpers ───────────────────────────────────────────────────────────

def _tab_pdf_url(t: dict, ctx_id: str, n: int) -> None:
    pdf_url = st.text_input(t["label_pdf_url"], placeholder=t["ph_pdf_url"], key=f"in_pdf_url_{n}")
    if st.button(t["btn_pdf_url"], key=f"btn_pdf_url_{n}") and pdf_url:
        if _ingest_with_feedback(t, api_post, "/ingest/pdf-url", {"url": pdf_url, "context_id": ctx_id}):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def _tab_web(t: dict, ctx_id: str, n: int) -> None:
    web_url = st.text_input(t["label_web_url"], placeholder=t["ph_web_url"], key=f"in_web_url_{n}")
    if st.button(t["btn_web_url"], key=f"btn_web_url_{n}") and web_url:
        if _ingest_with_feedback(t, api_post, "/ingest/web-url", {"url": web_url, "context_id": ctx_id}):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def _tab_upload(t: dict, ctx_id: str, n: int) -> None:
    uploaded = st.file_uploader(t["label_upload"], type=["pdf"], key=f"in_upload_{n}")
    if uploaded and st.button(t["btn_upload"], key=f"btn_upload_{n}"):
        files = {
            "file": (uploaded.name, uploaded.getvalue(), "application/pdf"),
            "context_id": (None, ctx_id),
        }
        if _ingest_with_feedback(t, api_post, "/ingest/pdf-upload", files=files):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def _tab_text(t: dict, ctx_id: str, n: int) -> None:
    text_title = st.text_input(t["label_text_title"], value=t["text_default_title"], key=f"in_title_{n}")
    pasted = st.text_area(t["label_text_area"], height=140, key=f"in_text_{n}")
    if st.button(t["btn_text"], key=f"btn_text_{n}"):
        if len(pasted.strip()) >= 50:
            if _ingest_with_feedback(
                t, api_post, "/ingest/raw-text",
                {"text": pasted, "title": text_title, "context_id": ctx_id},
            ):
                st.session_state["_ingest_n"] = n + 1
                st.rerun()
        else:
            st.warning(t["warn_too_short"])


def _tab_image(t: dict, ctx_id: str, n: int) -> None:
    uploaded_img = st.file_uploader(
        t["label_image_upload"],
        type=["png", "jpg", "jpeg", "webp"],
        key=f"in_image_{n}",
    )
    detail_level = st.radio(
        t["label_detail_level"],
        options=["quick", "standard", "detailed"],
        format_func=lambda x: t[f"detail_{x}"],
        index=1,
        horizontal=True,
        key=f"in_detail_{n}",
    )
    if uploaded_img and st.button(t["btn_image"], key=f"btn_image_{n}"):
        files = {
            "file": (uploaded_img.name, uploaded_img.getvalue(), uploaded_img.type or "image/jpeg"),
            "context_id": (None, ctx_id),
            "detail_level": (None, detail_level),
        }
        if _ingest_with_feedback(t, api_post, "/ingest/image-upload", files=files):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def _tab_audio(t: dict, ctx_id: str, n: int) -> None:
    st.caption(t["audio_hint"])
    uploaded_audio = st.file_uploader(
        t["label_audio_upload"],
        type=["mp3", "wav", "m4a", "ogg", "flac", "webm"],
        key=f"in_audio_{n}",
    )
    if uploaded_audio and st.button(t["btn_audio"], key=f"btn_audio_{n}"):
        files = {
            "file": (uploaded_audio.name, uploaded_audio.getvalue(), uploaded_audio.type or "audio/mpeg"),
            "context_id": (None, ctx_id),
        }
        if _ingest_with_feedback(t, api_post_audio, "/ingest/audio-upload", files=files):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


# ── Panel sidebar (context list screen) ────────────────────────────────────────

def panel_sidebar(t: dict) -> None:
    _lang_toggle(t)
    st.divider()
    st.markdown("#### 📚 ResearchMind")
    st.caption(t["app_caption"])


# ── Context sidebar ──────────────────────────────────────────────────────────────

_HISTORY_ICONS: dict[str, str] = {"source_added": "➕", "source_edited": "✏️"}


def _sources_accordion(t: dict, ctx_id: str) -> None:
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
            title = src.get("title") or doc_id[:8]
            s_type = src.get("source_type", "")
            chunks = src.get("chunk_count", 0)
            date = src.get("ingested_at", "")[:10]
            col_info, col_edit_btn, col_del_btn = st.columns([5, 1, 1])
            with col_info:
                st.markdown(f"**{title}**")
                st.caption(f"{s_type} · {chunks} {t['ctx_chunks']} · {date}")
            with col_edit_btn:
                if st.button("✏️", key=f"src_edit_{doc_id}", help=t["ctx_edit_source"]):
                    _edit_source_dialog(ctx_id, doc_id, t)
            with col_del_btn:
                if st.button("🗑️", key=f"src_del_{doc_id}", help=t["ctx_delete_source"]):
                    try:
                        api_delete(f"/contexts/{ctx_id}/sources/{doc_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(t["error_prefix"].format(e))


def _history_accordion(t: dict, ctx_id: str) -> None:
    with st.expander(t["ctx_history_section"], expanded=False):
        try:
            entries = api_get(f"/contexts/{ctx_id}/history")
        except Exception:
            entries = []
        if not entries:
            st.caption(t["ctx_history_empty"])
            return
        for entry in entries[:30]:
            ts = entry.get("timestamp", "")[:16].replace("T", " ")
            action = entry.get("action", "")
            detail = entry.get("detail", "")
            icon = _HISTORY_ICONS.get(action, "•")
            st.markdown(f"{icon} `{ts}` {detail}")


def context_sidebar(t: dict, ctx: dict) -> None:
    ctx_id = ctx["context_id"]

    # ── Navigation row ──────────────────────────────────────────────────────────
    col_back, col_lang = st.columns([3, 1])
    with col_back:
        if st.button(t["ctx_back"], use_container_width=True):
            st.session_state.active_context = None
            st.session_state.messages = []
            st.session_state.pop("editing_context_name", None)
            st.rerun()
    with col_lang:
        _lang_toggle(t)

    st.divider()

    # ── Context name + rename ───────────────────────────────────────────────────
    col_name, col_edit = st.columns([5, 1])
    with col_name:
        st.markdown(f"**{ctx['name']}**")
    with col_edit:
        if st.button("✏️", key="btn_rename_ctx", help=t["ctx_rename"]):
            _rename_dialog(ctx_id, ctx["name"], t)

    st.divider()

    # ── Ingest success banner ───────────────────────────────────────────────────
    if msg := st.session_state.pop("_ingest_ok", None):
        st.success(msg)

    # ── Add Source accordion ────────────────────────────────────────────────────
    with st.expander(t["ctx_add_source"], expanded=True):
        n = st.session_state.get("_ingest_n", 0)
        tab_pdf_url, tab_web, tab_upload, tab_text, tab_image, tab_audio = st.tabs([
            t["tab_pdf_url"], t["tab_web"], t["tab_upload"], t["tab_text"], t["tab_image"], t["tab_audio"],
        ])
        with tab_pdf_url:
            _tab_pdf_url(t, ctx_id, n)
        with tab_web:
            _tab_web(t, ctx_id, n)
        with tab_upload:
            _tab_upload(t, ctx_id, n)
        with tab_text:
            _tab_text(t, ctx_id, n)
        with tab_image:
            _tab_image(t, ctx_id, n)
        with tab_audio:
            _tab_audio(t, ctx_id, n)

    # ── Sources + History accordions ────────────────────────────────────────────
    _sources_accordion(t, ctx_id)
    _history_accordion(t, ctx_id)
