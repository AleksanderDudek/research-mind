import streamlit as st

from ._en import EN
from ._pl import PL

_TRANSLATIONS: dict[str, dict[str, str]] = {"en": EN, "pl": PL}


def get_lang() -> str:
    lang = st.query_params.get("lang", "en")
    return lang if lang in _TRANSLATIONS else "en"


def get_translations(lang: str) -> dict[str, str]:
    return _TRANSLATIONS.get(lang, EN)
