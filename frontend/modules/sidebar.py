import streamlit as st

from .api_client import api_post

_SKELETON = """
<div class="skeleton" style="width:80%"></div>
<div class="skeleton" style="width:60%"></div>
<div class="skeleton" style="width:70%"></div>
"""


def _ingest_with_status(T: dict[str, str], fn, *args, **kwargs) -> None:
    with st.status(T["status_sending"], expanded=True) as status:
        try:
            st.write(T["status_processing"])
            res = fn(*args, **kwargs)
            status.update(label=T["status_done"], state="complete", expanded=False)
            st.success(T["success_chunks"].format(res["chunks_ingested"]))
            st.json(res)
        except Exception as e:
            status.update(label=T["status_error"], state="error", expanded=True)
            st.error(T["error_prefix"].format(e))


@st.fragment
def sidebar_content(T: dict[str, str], lang: str) -> None:
    st.markdown(
        f'<a href="?lang={T["lang_toggle_target"]}" target="_self">{T["lang_toggle"]}</a>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.title(T["sidebar_title"])

    tab_pdf_url, tab_web, tab_upload, tab_text = st.tabs([
        T["tab_pdf_url"], T["tab_web"], T["tab_upload"], T["tab_text"],
    ])

    with tab_pdf_url:
        pdf_url = st.text_input(T["label_pdf_url"], placeholder=T["ph_pdf_url"], key="in_pdf_url")
        if st.button(T["btn_pdf_url"], key="pdf_url_btn") and pdf_url:
            _ingest_with_status(T, api_post, "/ingest/pdf-url", {"url": pdf_url})

    with tab_web:
        web_url = st.text_input(T["label_web_url"], placeholder=T["ph_web_url"], key="in_web_url")
        if st.button(T["btn_web_url"], key="web_url_btn") and web_url:
            _ingest_with_status(T, api_post, "/ingest/web-url", {"url": web_url})

    with tab_upload:
        uploaded = st.file_uploader(T["label_upload"], type=["pdf"], key="in_upload")
        if uploaded and st.button(T["btn_upload"], key="upload_btn"):
            files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
            _ingest_with_status(T, api_post, "/ingest/pdf-upload", files=files)

    with tab_text:
        text_title = st.text_input(T["label_text_title"], value="Manual paste", key="in_title")
        pasted_text = st.text_area(T["label_text_area"], height=200, key="in_text")
        if st.button(T["btn_text"], key="text_btn"):
            if len(pasted_text.strip()) >= 50:
                _ingest_with_status(
                    T, api_post, "/ingest/raw-text",
                    {"text": pasted_text, "title": text_title},
                )
            else:
                st.warning(T["warn_too_short"])
