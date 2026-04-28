from pathlib import Path

import streamlit.components.v1 as components

from .api_client import BACKEND_URL

_JS_PATH = Path(__file__).parent / "assets" / "voice.js"


def inject_voice_fab() -> None:
    """
    Inject both FABs (mic + voice) and the auto-record loop into the parent page.
    The JS is stored in assets/voice.js; %%BACKEND%% is replaced at runtime.
    """
    js = _JS_PATH.read_text().replace("%%BACKEND%%", BACKEND_URL.rstrip("/"))
    components.html(f"<script>{js}</script>", height=0)
