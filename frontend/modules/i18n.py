import streamlit as st

TRANSLATIONS: dict[str, dict[str, str]] = {
    "pl": {
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


def get_lang() -> str:
    lang = st.query_params.get("lang", "en")
    return lang if lang in TRANSLATIONS else "en"


def get_T(lang: str) -> dict[str, str]:
    return TRANSLATIONS[lang]
