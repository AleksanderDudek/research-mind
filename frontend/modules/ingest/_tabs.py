"""Six ingest-source tabs (PDF URL, web, upload, text, image, audio)."""
import streamlit as st

from ..api_client import api_post, api_post_audio


def _ingest_with_feedback(t: dict, fn, *args, **kwargs) -> bool:
    with st.spinner(t["status_sending"]):
        try:
            res = fn(*args, **kwargs)
            st.session_state["_ingest_ok"] = t["ctx_ingest_success"].format(res["chunks_ingested"])
            return True
        except Exception as e:
            st.error(t["error_prefix"].format(e))
            return False


def tab_pdf_url(t: dict, ctx_id: str, n: int) -> None:
    pdf_url = st.text_input(t["label_pdf_url"], placeholder=t["ph_pdf_url"], key=f"in_pdf_url_{n}")
    if st.button(t["btn_pdf_url"], key=f"btn_pdf_url_{n}") and pdf_url:
        if _ingest_with_feedback(t, api_post, "/ingest/pdf-url", {"url": pdf_url, "context_id": ctx_id}):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def tab_web(t: dict, ctx_id: str, n: int) -> None:
    web_url = st.text_input(t["label_web_url"], placeholder=t["ph_web_url"], key=f"in_web_url_{n}")
    if st.button(t["btn_web_url"], key=f"btn_web_url_{n}") and web_url:
        if _ingest_with_feedback(t, api_post, "/ingest/web-url", {"url": web_url, "context_id": ctx_id}):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def tab_upload(t: dict, ctx_id: str, n: int) -> None:
    uploaded = st.file_uploader(t["label_upload"], type=["pdf"], key=f"in_upload_{n}")
    if uploaded and st.button(t["btn_upload"], key=f"btn_upload_{n}"):
        files = {
            "file":       (uploaded.name, uploaded.getvalue(), "application/pdf"),
            "context_id": (None, ctx_id),
        }
        if _ingest_with_feedback(t, api_post, "/ingest/pdf-upload", files=files):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def tab_text(t: dict, ctx_id: str, n: int) -> None:
    text_title = st.text_input(t["label_text_title"], value=t["text_default_title"], key=f"in_title_{n}")
    pasted     = st.text_area(t["label_text_area"], height=140, key=f"in_text_{n}")
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


def tab_image(t: dict, ctx_id: str, n: int) -> None:
    uploaded_img = st.file_uploader(
        t["label_image_upload"], type=["png", "jpg", "jpeg", "webp"], key=f"in_image_{n}",
    )
    detail_level = st.radio(
        t["label_detail_level"],
        options=["quick", "standard", "detailed"],
        format_func=lambda x: t[f"detail_{x}"],
        index=1, horizontal=True, key=f"in_detail_{n}",
    )
    if uploaded_img and st.button(t["btn_image"], key=f"btn_image_{n}"):
        files = {
            "file":         (uploaded_img.name, uploaded_img.getvalue(), uploaded_img.type or "image/jpeg"),
            "context_id":   (None, ctx_id),
            "detail_level": (None, detail_level),
        }
        if _ingest_with_feedback(t, api_post, "/ingest/image-upload", files=files):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()


def tab_audio(t: dict, ctx_id: str, n: int) -> None:
    st.caption(t["audio_hint"])
    uploaded_audio = st.file_uploader(
        t["label_audio_upload"], type=["mp3", "wav", "m4a", "ogg", "flac", "webm"],
        key=f"in_audio_{n}",
    )
    if uploaded_audio and st.button(t["btn_audio"], key=f"btn_audio_{n}"):
        files = {
            "file":       (uploaded_audio.name, uploaded_audio.getvalue(), uploaded_audio.type or "audio/mpeg"),
            "context_id": (None, ctx_id),
        }
        if _ingest_with_feedback(t, api_post_audio, "/ingest/audio-upload", files=files):
            st.session_state["_ingest_n"] = n + 1
            st.rerun()
