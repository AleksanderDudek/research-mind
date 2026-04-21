import os

import streamlit as st
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

st.set_page_config(page_title="ResearchMind", page_icon="📚", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []


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


# ─── SIDEBAR: Ingestion ──────────────────────────────────────────
with st.sidebar:
    st.title("📥 Dodaj źródło")

    tab1, tab2, tab3, tab4 = st.tabs(["PDF URL", "Strona WWW", "Upload PDF", "Tekst"])

    with tab1:
        pdf_url = st.text_input("Link do PDF", placeholder="https://arxiv.org/pdf/...")
        if st.button("Pobierz i zindeksuj PDF", key="pdf_url_btn") and pdf_url:
            with st.spinner("Pobieranie i przetwarzanie..."):
                try:
                    res = api_post("/ingest/pdf-url", {"url": pdf_url})
                    st.success(f"Zindeksowano {res['chunks_ingested']} fragmentów")
                    st.json(res)
                except Exception as e:
                    st.error(f"Błąd: {e}")

    with tab2:
        web_url = st.text_input("Link do strony", placeholder="https://...")
        if st.button("Pobierz i zindeksuj stronę", key="web_url_btn") and web_url:
            with st.spinner("Scrapowanie..."):
                try:
                    res = api_post("/ingest/web-url", {"url": web_url})
                    st.success(f"Zindeksowano {res['chunks_ingested']} fragmentów")
                    st.json(res)
                except Exception as e:
                    st.error(f"Błąd: {e}")

    with tab3:
        uploaded = st.file_uploader("Wgraj plik PDF", type=["pdf"])
        if uploaded and st.button("Zindeksuj plik", key="upload_btn"):
            with st.spinner("Przetwarzanie..."):
                try:
                    files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                    res = api_post("/ingest/pdf-upload", files=files)
                    st.success(f"Zindeksowano {res['chunks_ingested']} fragmentów")
                    st.json(res)
                except Exception as e:
                    st.error(f"Błąd: {e}")

    with tab4:
        text_title = st.text_input("Tytuł (opcjonalnie)", value="Manual paste")
        pasted_text = st.text_area("Wklej tekst", height=200)
        if st.button("Zindeksuj tekst", key="text_btn"):
            if len(pasted_text.strip()) >= 50:
                with st.spinner("Indeksowanie..."):
                    try:
                        res = api_post("/ingest/raw-text", {"text": pasted_text, "title": text_title})
                        st.success(f"Zindeksowano {res['chunks_ingested']} fragmentów")
                    except Exception as e:
                        st.error(f"Błąd: {e}")
            else:
                st.warning("Tekst musi mieć co najmniej 50 znaków.")


# ─── MAIN: Chat ──────────────────────────────────────────────────
st.title("📚 ResearchMind")
st.caption("Analiza badań naukowych z agentem AI")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sources" in msg and msg["sources"]:
            with st.expander(f"Źródła ({len(msg['sources'])})"):
                for i, src in enumerate(msg["sources"], 1):
                    st.markdown(
                        f"**[{i}]** `{src.get('source', 'unknown')}` "
                        f"(score: {src.get('score', 0):.3f})"
                    )
                    st.text(str(src.get("text", ""))[:500] + "...")

if prompt := st.chat_input("Zadaj pytanie o swoje dokumenty..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent myśli..."):
            try:
                res = api_post("/query/ask", {"question": prompt})
                answer = res["answer"]
                st.markdown(answer)
                st.caption(
                    f"Akcja: `{res['action_taken']}` | "
                    f"Iteracji: {res['iterations']} | "
                    f"Krytyk: {res.get('critique', {}).get('score', '?')}/5"
                )
                if res.get("sources"):
                    with st.expander(f"Źródła ({len(res['sources'])})"):
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
                st.error(f"Błąd: {e}")
