from pathlib import Path
import streamlit as st

_CSS_PATH = Path(__file__).parent / "assets" / "styles.css"


def inject_styles() -> None:
    css = _CSS_PATH.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
