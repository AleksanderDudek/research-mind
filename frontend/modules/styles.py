import streamlit as st

_CSS = """
<style>
/* ── Hide Streamlit sidebar entirely ────────────────────────────────────────── */
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

/* ── Hide Streamlit toolbar ─────────────────────────────────────────────────── */
header[data-testid="stHeader"] {
    display: none !important;
}

/* ── Mobile-first layout ────────────────────────────────────────────────────── */
.block-container {
    max-width: 640px !important;
    padding: 1.5rem 1.25rem 5rem !important;
    margin: 0 auto !important;
}

/* ── Top progress bar during reruns ─────────────────────────────────────────── */
div[data-testid="stApp"][data-stale="true"]::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(
        90deg, transparent 0%, #4F46E5 40%, #818CF8 60%, transparent 100%
    );
    background-size: 300% 100%;
    animation: topbar 1.2s ease-in-out infinite;
    z-index: 999999;
}
@keyframes topbar {
    0%   { background-position: 100% 0; }
    100% { background-position: -100% 0; }
}

/* ── Skeleton shimmer for loading state ─────────────────────────────────────── */
.skeleton {
    background: linear-gradient(90deg, #F1F5F9 25%, #E2E8F0 50%, #F1F5F9 75%);
    background-size: 200% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
    border-radius: 6px;
    height: 16px;
    margin: 6px 0;
}
@keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ── Sticky page header (back/name/rename row or home title) ────────────────── */
.block-container > [data-testid="stVerticalBlock"] > div:first-child {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(255, 255, 255, 0.97);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    padding-bottom: 0.35rem;
}

/* ── Keep columns horizontal on narrow screens ──────────────────────────────── */
[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    align-items: flex-start !important;
    gap: 0.4rem !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 0 !important;
}

/* ── Tighten element vertical spacing ───────────────────────────────────────── */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    gap: 0.25rem !important;
}

/* ── Tab label spacing (emoji ↔ text) ───────────────────────────────────────── */
[data-testid="stTab"] p {
    letter-spacing: 0.01em;
}

/* ── Chat message fade-in ───────────────────────────────────────────────────── */
div[data-testid="stChatMessage"] {
    animation: msg-in 0.2s ease-out;
}
@keyframes msg-in {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Card separator ─────────────────────────────────────────────────────────── */
.rm-sep {
    height: 1px;
    background: #F1F5F9;
    margin: 0.25rem 0 0.35rem;
}

/* ── Voice toggle buttons — hidden off-screen, JS clicks them ───────────────── */
.st-key-rm-voice-on,
.st-key-rm-voice-off {
    position: fixed !important;
    left: -9999px !important;
    top: -9999px !important;
    opacity: 0 !important;
    z-index: -1 !important;
}

/* ── Voice mode: hide chat input, hide mic FAB ───────────────────────────────── */
body:has(#rm-voice-active) [data-testid="stChatInputContainer"] {
    display: none !important;
}
body:has(#rm-voice-active) #rm-mic-fab {
    opacity: 0 !important;
    pointer-events: none !important;
}

/* ── Voice circle — centred, state driven by body class (not element className) ─ */
#rm-voice-circle-main {
    margin: 3rem auto 2rem;
}
/* Thinking state: body class set by JS so React can't overwrite it */
body.rm-voice-thinking #rm-voice-circle-main {
    background: radial-gradient(circle at 35% 35%, #6EE7B7, #10B981) !important;
    animation: rm-spin 1.4s linear infinite !important;
}

/* ── Voice conversation animated circle ─────────────────────────────────────── */
.rm-voice-circle {
    width: 88px;
    height: 88px;
    border-radius: 50%;
    margin: 1.5rem auto;
    background: radial-gradient(circle at 35% 35%, #818CF8, #4F46E5);
    box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.35);
    animation: rm-idle 2.5s ease-in-out infinite;
}
.rm-voice-circle--thinking {
    background: radial-gradient(circle at 35% 35%, #6EE7B7, #10B981);
    animation: rm-spin 1.4s linear infinite;
}
@keyframes rm-idle {
    0%, 100% { transform: scale(1);    box-shadow: 0 0 0  0px rgba(79, 70, 229, 0.35); }
    50%       { transform: scale(1.1); box-shadow: 0 0 0 16px rgba(79, 70, 229, 0);    }
}
@keyframes rm-spin {
    0%   { transform: scale(1)   rotate(0deg); }
    50%  { transform: scale(1.1) rotate(180deg); }
    100% { transform: scale(1)   rotate(360deg); }
}

/* ── Pending question recovery banner ───────────────────────────────────────── */
.rm-pending {
    background: #FFFBEB;
    border: 1px solid #FCD34D;
    border-left: 4px solid #F59E0B;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
}

/* ── App header (inline title + lang toggle) ────────────────────────────────── */
.rm-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.15rem;
}
.rm-header-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.2;
}
.rm-header-lang a {
    color: #4F46E5;
    text-decoration: none;
    font-size: 0.85rem;
}

/* ── Context view header ────────────────────────────────────────────────────── */
.rm-ctx-title {
    font-size: 1rem;
    font-weight: 600;
    color: #0F172A;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
