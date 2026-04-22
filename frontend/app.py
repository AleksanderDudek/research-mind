import os

import httpx
import streamlit as st
import streamlit.components.v1 as components

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

# ── i18n ───────────────────────────────────────────────────────────────────────

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
        "status_sending": "Wysyłanie do backendu...",
        "status_processing": "Przetwarzanie dokumentu...",
        "status_done": "Gotowe!",
        "status_error": "Błąd",
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
        "status_sending": "Sending to backend...",
        "status_processing": "Processing document...",
        "status_done": "Done!",
        "status_error": "Error",
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

# ── Resolve language (pure dict read — no Streamlit rendering) ────────────────

lang = st.query_params.get("lang", "en")
if lang not in TRANSLATIONS:
    lang = "en"
T = TRANSLATIONS[lang]

# ── Page config — must be the first Streamlit command ─────────────────────────

st.set_page_config(page_title=T["page_title"], page_icon="📚", layout="wide")

# ── Browser language detection (redirect if ?lang not yet in URL) ─────────────

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

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Global CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Top loading bar while Streamlit is rerunning */
div[data-testid="stApp"][data-stale="true"]::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        #FF4B4B 40%,
        #FF4B4B 60%,
        transparent 100%
    );
    background-size: 300% 100%;
    animation: topbar 1.2s ease-in-out infinite;
    z-index: 999999;
}
@keyframes topbar {
    0%   { background-position: 100% 0; }
    100% { background-position: -100% 0; }
}

/* Dim content while stale instead of freezing visually */
div[data-testid="stApp"][data-stale="true"] > div {
    opacity: 0.6;
    transition: opacity 0.15s ease;
    pointer-events: none;
}
div[data-testid="stApp"][data-stale="false"] > div {
    opacity: 1;
    transition: opacity 0.2s ease;
}

/* Skeleton pulse for chat messages */
.skeleton {
    background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%);
    background-size: 200% 100%;
    animation: skeleton-pulse 1.4s infinite;
    border-radius: 6px;
    height: 16px;
    margin: 6px 0;
}
@keyframes skeleton-pulse {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Smooth fade-in for new chat messages */
div[data-testid="stChatMessage"] {
    animation: msg-in 0.25s ease-out;
}
@keyframes msg-in {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
</style>
""", unsafe_allow_html=True)


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


def _ingest_with_status(fn, *args, **kwargs):
    """Run an ingestion call wrapped in st.status for step-by-step feedback."""
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


# ── SIDEBAR — isolated fragment (won't rerun chat on submit) ───────────────────

@st.fragment
def sidebar_content() -> None:
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
        pdf_url = st.text_input(T["label_pdf_url"], placeholder=T["ph_pdf_url"], key="in_pdf_url")
        if st.button(T["btn_pdf_url"], key="pdf_url_btn") and pdf_url:
            _ingest_with_status(api_post, "/ingest/pdf-url", {"url": pdf_url})

    with tab2:
        web_url = st.text_input(T["label_web_url"], placeholder=T["ph_web_url"], key="in_web_url")
        if st.button(T["btn_web_url"], key="web_url_btn") and web_url:
            _ingest_with_status(api_post, "/ingest/web-url", {"url": web_url})

    with tab3:
        uploaded = st.file_uploader(T["label_upload"], type=["pdf"], key="in_upload")
        if uploaded and st.button(T["btn_upload"], key="upload_btn"):
            files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
            _ingest_with_status(api_post, "/ingest/pdf-upload", files=files)

    with tab4:
        text_title = st.text_input(T["label_text_title"], value="Manual paste", key="in_title")
        pasted_text = st.text_area(T["label_text_area"], height=200, key="in_text")
        if st.button(T["btn_text"], key="text_btn"):
            if len(pasted_text.strip()) >= 50:
                _ingest_with_status(api_post, "/ingest/raw-text", {"text": pasted_text, "title": text_title})
            else:
                st.warning(T["warn_too_short"])


with st.sidebar:
    sidebar_content()


# ── MAIN CHAT — isolated fragment (won't rerun sidebar on message) ─────────────

@st.fragment
def chat_content() -> None:
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
            # Show skeleton while waiting
            skeleton_slot = st.empty()
            skeleton_slot.markdown("""
<div class="skeleton" style="width:80%"></div>
<div class="skeleton" style="width:60%"></div>
<div class="skeleton" style="width:70%"></div>
""", unsafe_allow_html=True)

            with st.spinner(T["spinner_agent"]):
                try:
                    res = api_post("/query/ask", {"question": prompt})
                    answer = res["answer"]
                    skeleton_slot.empty()
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
                    skeleton_slot.empty()
                    st.error(T["error_prefix"].format(e))


chat_content()
