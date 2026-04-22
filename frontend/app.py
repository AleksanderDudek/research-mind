import os

import httpx
import streamlit as st
import streamlit.components.v1 as components

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

# ── i18n ──────────────────────────────────────────────────────────────────────

TRANSLATIONS: dict[str, dict[str, str]] = {
    "pl": {
        "page_title": "ResearchMind",
        "app_title": "📚 ResearchMind",
        "app_caption": "Analiza badań naukowych z agentem AI",
        "sidebar_title": "📥 Dodaj źródło",
        "tab_pdf_url": "PDF URL",
        "tab_web": "Strona WWW",
        "tab_upload": "Upload PDF",
        "tab_text": "Tekst",
        "label_pdf_url": "Link do PDF",
        "ph_pdf_url": "https://arxiv.org/pdf/...",
        "btn_pdf_url": "Pobierz i zindeksuj PDF",
        "label_web_url": "Link do strony",
        "ph_web_url": "https://...",
        "btn_web_url": "Pobierz i zindeksuj stronę",
        "label_upload": "Wgraj plik PDF",
        "btn_upload": "Zindeksuj plik",
        "label_text_title": "Tytuł (opcjonalnie)",
        "label_text_area": "Wklej tekst",
        "btn_text": "Zindeksuj tekst",
        "spinner_pdf": "Pobieranie i przetwarzanie...",
        "spinner_web": "Scrapowanie...",
        "spinner_upload": "Przetwarzanie...",
        "spinner_index": "Indeksowanie...",
        "spinner_agent": "Agent myśli...",
        "success_chunks": "Zindeksowano {} fragmentów",
        "warn_too_short": "Tekst musi mieć co najmniej 50 znaków.",
        "error_prefix": "Błąd: {}",
        "sources_label": "Źródła ({})",
        "chat_placeholder": "Zadaj pytanie o swoje dokumenty...",
        "action_label": "Akcja: `{}` | Iteracji: {} | Krytyk: {}/5",
        "lang_toggle": "🇬🇧 English",
        "lang_toggle_target": "en",
    },
    "en": {
        "page_title": "ResearchMind",
        "app_title": "📚 ResearchMind",
        "app_caption": "Scientific research analysis with AI agent",
        "sidebar_title": "📥 Add source",
        "tab_pdf_url": "PDF URL",
        "tab_web": "Web page",
        "tab_upload": "Upload PDF",
        "tab_text": "Text",
        "label_pdf_url": "PDF link",
        "ph_pdf_url": "https://arxiv.org/pdf/...",
        "btn_pdf_url": "Fetch and index PDF",
        "label_web_url": "Page link",
        "ph_web_url": "https://...",
        "btn_web_url": "Fetch and index page",
        "label_upload": "Upload PDF file",
        "btn_upload": "Index file",
        "label_text_title": "Title (optional)",
        "label_text_area": "Paste text",
        "btn_text": "Index text",
        "spinner_pdf": "Downloading and processing...",
        "spinner_web": "Scraping...",
        "spinner_upload": "Processing...",
        "spinner_index": "Indexing...",
        "spinner_agent": "Agent is thinking...",
        "success_chunks": "Indexed {} chunks",
        "warn_too_short": "Text must be at least 50 characters.",
        "error_prefix": "Error: {}",
        "sources_label": "Sources ({})",
        "chat_placeholder": "Ask a question about your documents...",
        "action_label": "Action: `{}` | Iterations: {} | Critic: {}/5",
        "lang_toggle": "🇵🇱 Polski",
        "lang_toggle_target": "pl",
    },
}

# ── Browser language detection (runs once, before lang param is set) ──────────

components.html("""
<script>
    const params = new URLSearchParams(window.parent.location.search);
    if (!params.has('lang')) {
        const detected = (navigator.language || 'en').toLowerCase();
        params.set('lang', detected.startsWith('pl') ? 'pl' : 'en');
        window.parent.location.search = params.toString();
    }
</script>
""", height=0)

# ── Resolve language ───────────────────────────────────────────────────────────

lang = st.query_params.get("lang", "en")
if lang not in TRANSLATIONS:
    lang = "en"
T = TRANSLATIONS[lang]

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(page_title=T["page_title"], page_icon="📚", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Helpers ────────────────────────────────────────────────────────────────────

def api_post(path: str, json_data: dict | None = None, files: dict | None = None) -> dict:
    with httpx.Client(timeout=180.0) as client:
        if files:
            r = client.post(f"{BACKEND_URL}{path}", files=files)
        else:
            r = client.post(f"{BACKEND_URL}{path}", json=json_data)
        if r.is_error:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            raise ValueError(detail)
        return r.json()


# ── SIDEBAR ────────────────────────────────────────────────────────────────────

with st.sidebar:
    # Language toggle
    st.markdown(
        f'<a href="?lang={T["lang_toggle_target"]}" target="_self">{T["lang_toggle"]}</a>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.title(T["sidebar_title"])

    tab1, tab2, tab3, tab4 = st.tabs([
        T["tab_pdf_url"], T["tab_web"], T["tab_upload"], T["tab_text"]
    ])

    with tab1:
        pdf_url = st.text_input(T["label_pdf_url"], placeholder=T["ph_pdf_url"])
        if st.button(T["btn_pdf_url"], key="pdf_url_btn") and pdf_url:
            with st.spinner(T["spinner_pdf"]):
                try:
                    res = api_post("/ingest/pdf-url", {"url": pdf_url})
                    st.success(T["success_chunks"].format(res["chunks_ingested"]))
                    st.json(res)
                except Exception as e:
                    st.error(T["error_prefix"].format(e))

    with tab2:
        web_url = st.text_input(T["label_web_url"], placeholder=T["ph_web_url"])
        if st.button(T["btn_web_url"], key="web_url_btn") and web_url:
            with st.spinner(T["spinner_web"]):
                try:
                    res = api_post("/ingest/web-url", {"url": web_url})
                    st.success(T["success_chunks"].format(res["chunks_ingested"]))
                    st.json(res)
                except Exception as e:
                    st.error(T["error_prefix"].format(e))

    with tab3:
        uploaded = st.file_uploader(T["label_upload"], type=["pdf"])
        if uploaded and st.button(T["btn_upload"], key="upload_btn"):
            with st.spinner(T["spinner_upload"]):
                try:
                    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                    res = api_post("/ingest/pdf-upload", files=files)
                    st.success(T["success_chunks"].format(res["chunks_ingested"]))
                    st.json(res)
                except Exception as e:
                    st.error(T["error_prefix"].format(e))

    with tab4:
        text_title = st.text_input(T["label_text_title"], value="Manual paste")
        pasted_text = st.text_area(T["label_text_area"], height=200)
        if st.button(T["btn_text"], key="text_btn"):
            if len(pasted_text.strip()) >= 50:
                with st.spinner(T["spinner_index"]):
                    try:
                        res = api_post("/ingest/raw-text", {"text": pasted_text, "title": text_title})
                        st.success(T["success_chunks"].format(res["chunks_ingested"]))
                    except Exception as e:
                        st.error(T["error_prefix"].format(e))
            else:
                st.warning(T["warn_too_short"])


# ── MAIN: Chat ─────────────────────────────────────────────────────────────────

st.title(T["app_title"])
st.caption(T["app_caption"])

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sources" in msg and msg["sources"]:
            with st.expander(T["sources_label"].format(len(msg["sources"]))):
                for i, src in enumerate(msg["sources"], 1):
                    st.markdown(
                        f"**[{i}]** `{src.get('source', 'unknown')}` "
                        f"(score: {src.get('score', 0):.3f})"
                    )
                    st.text(str(src.get("text", ""))[:500] + "...")

if prompt := st.chat_input(T["chat_placeholder"]):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(T["spinner_agent"]):
            try:
                res = api_post("/query/ask", {"question": prompt})
                answer = res["answer"]
                st.markdown(answer)
                st.caption(T["action_label"].format(
                    res["action_taken"], res["iterations"],
                    res.get("critique", {}).get("score", "?")
                ))
                if res.get("sources"):
                    with st.expander(T["sources_label"].format(len(res["sources"]))):
                        for i, src in enumerate(res["sources"], 1):
                            st.markdown(
                                f"**[{i}]** `{src.get('source', 'unknown')}` "
                                f"(score: {src.get('score', 0):.3f})"
                            )
                            st.text(str(src.get("text", ""))[:500] + "...")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": res.get("sources", []),
                })
            except Exception as e:
                st.error(T["error_prefix"].format(e))
