import streamlit as st

_CSS = """
<style>
/* ── Hide Streamlit sidebar entirely ────────────────────────────────────────── */
section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
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

/* ── Chat message fade-in ───────────────────────────────────────────────────── */
div[data-testid="stChatMessage"] {
    animation: msg-in 0.2s ease-out;
}
@keyframes msg-in {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Context card rows (pure HTML elements, no Streamlit wrapper) ────────────── */
.rm-card {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 0.85rem 0 0.2rem;
}
.rm-card-name {
    font-weight: 600;
    font-size: 1rem;
    color: #0F172A;
}
.rm-card-meta {
    font-size: 0.8rem;
    color: #94A3B8;
    white-space: nowrap;
    padding-left: 0.5rem;
}
.rm-sep {
    height: 1px;
    background: #F1F5F9;
    margin: 0.5rem 0 0.25rem;
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
