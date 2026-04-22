import streamlit as st

_CSS = """
<style>
/* Top progress bar during Streamlit reruns */
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

/* Skeleton pulse for chat loading placeholder */
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
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
