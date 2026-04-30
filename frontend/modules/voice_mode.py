"""Voice mode Streamlit page — Step 11 UX polish.

Visuals
-------
- Large animated circle above the mic button.
  · gray breathing (IDLE)
  · red pulsing    (LISTENING — detected via JS MutationObserver)
  · amber spinning (PROCESSING)
- Real-time volume bar via Web Audio AnalyserNode (JS-driven).
- Editable transcripts: ✏️ icon on each turn, inline edit form.
- LOW_CONFIDENCE: prominent bordered confirmation card.
- LIKELY_NOISE: auto-dismissing st.toast.

State
-----
All mutable state lives in st.session_state["voice_state"] (single dict).
st.rerun() is called only at defined transition points (after processing,
after confirmation, after edit).
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as _components
from streamlit_mic_recorder import mic_recorder

from .api_client import api_post_audio

# ── Gate decision constants ────────────────────────────────────────────────────
_GATE_VALID          = "valid"
_GATE_LOW_CONFIDENCE = "low_confidence"
_GATE_LIKELY_NOISE   = "likely_noise"
_GATE_HALLUCINATION  = "hallucination"
_GATE_EMPTY          = "empty"

_VOICES = ["nova", "alloy", "echo", "fable", "onyx", "shimmer"]
_LANGS  = {"Auto": None, "English": "en", "Polski": "pl"}

_STATUS_TEXT = {
    "idle":       "Tap to speak",
    "processing": "Processing your voice…",
}

# ── CSS / JS helpers ──────────────────────────────────────────────────────────

_VOICE_CSS = """
<style>
/* ── Animated state circle ────────────────────────────────────────────────── */
.rm-voice-ind {
    width: 88px; height: 88px;
    border-radius: 50%;
    margin: 0.75rem auto 0.5rem;
    display: block;
    transition: background 0.3s ease;
}
.rm-voice-ind-idle {
    background: #D1D5DB;
    animation: rm-vi-breathe 2.8s ease-in-out infinite;
}
.rm-voice-ind-listening {
    background: #EF4444;
    animation: rm-vi-pulse 0.75s ease-in-out infinite;
}
.rm-voice-ind-processing {
    background: radial-gradient(circle at 35% 35%, #FCD34D, #F59E0B);
    animation: rm-vi-spin 1.1s linear infinite;
}
@keyframes rm-vi-breathe {
    0%,100% { transform: scale(1);    opacity: 0.55; }
    50%     { transform: scale(1.06); opacity: 0.80; }
}
@keyframes rm-vi-pulse {
    0%,100% { transform: scale(1);   box-shadow: 0 0 0  0px rgba(239,68,68,0.45); }
    50%     { transform: scale(1.12);box-shadow: 0 0 0 14px rgba(239,68,68,0);   }
}
@keyframes rm-vi-spin {
    0%   { transform: rotate(0deg)   scale(1);    }
    50%  { transform: rotate(180deg) scale(1.08); }
    100% { transform: rotate(360deg) scale(1);    }
}

/* ── Volume bar ───────────────────────────────────────────────────────────── */
.rm-vol-wrap {
    height: 5px;
    background: #F3F4F6;
    border-radius: 3px;
    margin: 0.25rem auto 0.75rem;
    max-width: 180px;
    overflow: hidden;
}
.rm-vol-bar {
    height: 100%;
    width: 0%;
    background: #EF4444;
    border-radius: 3px;
    transition: width 0.04s linear;
}

/* ── Status label ─────────────────────────────────────────────────────────── */
.rm-voice-status {
    text-align: center;
    font-size: 0.85rem;
    font-weight: 600;
    color: #6B7280;
    margin-bottom: 0.5rem;
}

/* ── Confirmation card ────────────────────────────────────────────────────── */
.rm-confirm-card {
    background: #FFF9C4;
    border: 1.5px solid #FBBF24;
    border-left: 4px solid #F59E0B;
    border-radius: 10px;
    padding: 0.85rem 1rem 0.5rem;
    margin-bottom: 1rem;
}
.rm-confirm-q {
    font-size: 1rem;
    font-weight: 600;
    color: #78350F;
    margin-bottom: 0.5rem;
}
</style>
"""

# JS template — %%BACKEND%% replaced at render time with the actual backend URL.
# Responsibilities:
#   1. Volume meter via Web Audio AnalyserNode (started when mic goes active).
#   2. State indicator class update (idle / listening / processing).
#   3. Barge-in: when new speech is detected while TTS plays —
#      a. Cancel browser speechSynthesis immediately.
#      b. POST %%BACKEND%%/voice/interrupt to stop any backend TTS streaming.
_VOICE_JS_TEMPLATE = """
(function() {
    const WIN = window.parent;
    const DOC = WIN.document;
    const BACKEND = "%%BACKEND%%";

    if (WIN._rmVoiceJsLoaded) return;
    WIN._rmVoiceJsLoaded = true;

    let micStream = null, analyser = null, rafId = null;

    function indicator() { return DOC.getElementById('rm-voice-ind'); }
    function volBar()    { return DOC.getElementById('rm-vol-bar');   }

    function setClass(cls) {
        const el = indicator();
        if (el) el.className = 'rm-voice-ind ' + cls;
    }

    function startVolume() {
        navigator.mediaDevices.getUserMedia({audio: true})
        .then(stream => {
            micStream = stream;
            const ctx = new AudioContext();
            analyser  = ctx.createAnalyser();
            analyser.fftSize = 256;
            ctx.createMediaStreamSource(stream).connect(analyser);
            const data = new Uint8Array(analyser.frequencyBinCount);
            function tick() {
                if (!micStream) return;
                analyser.getByteFrequencyData(data);
                const level = data.reduce((a,b)=>a+b,0) / data.length / 255;
                const bar = volBar();
                if (bar) bar.style.width = Math.round(level * 100) + '%';
                rafId = WIN.requestAnimationFrame(tick);
            }
            tick();
        }).catch(() => {});
    }

    function stopVolume() {
        if (micStream) { micStream.getTracks().forEach(t=>t.stop()); micStream = null; }
        if (rafId)     { WIN.cancelAnimationFrame(rafId); rafId = null; }
        const bar = volBar();
        if (bar) bar.style.width = '0%';
    }

    function isRecording() {
        for (const btn of DOC.querySelectorAll('button')) {
            if (/stop|recording/i.test(btn.textContent)) return true;
        }
        return false;
    }

    function barge_in() {
        // 1. Stop browser TTS immediately.
        if (WIN.speechSynthesis && WIN.speechSynthesis.speaking) {
            WIN.speechSynthesis.cancel();
        }
        // 2. Signal backend to abort any streaming TTS (fire-and-forget).
        fetch(BACKEND + '/voice/interrupt', {method: 'POST'}).catch(() => {});
    }

    let wasRecording = false;
    WIN.setInterval(() => {
        const now = isRecording();
        if (now && !wasRecording) {
            // New recording started — check for barge-in first.
            barge_in();
            setClass('rm-voice-ind-listening');
            startVolume();
        } else if (!now && wasRecording) {
            setClass('rm-voice-ind-idle');
            stopVolume();
        }
        wasRecording = now;
    }, 150);
})();
"""


def _inject_voice_ui() -> None:
    from .api_client import BACKEND_URL
    js = _VOICE_JS_TEMPLATE.replace("%%BACKEND%%", BACKEND_URL.rstrip("/"))
    st.markdown(_VOICE_CSS, unsafe_allow_html=True)
    _components.html(f"<script>{js}</script>", height=0)


# ── State helpers ─────────────────────────────────────────────────────────────

def _init(context_id: str | None) -> None:
    if "voice_state" not in st.session_state:
        st.session_state.voice_state = {
            "status":               "idle",
            "turns":                [],
            "pending_confirmation": None,
            "language":             None,
            "context_id":           context_id,
            "rec_n":                0,
            "tts_voice":            "nova",
        }


def _vs() -> dict:
    return st.session_state.voice_state


# ── History sub-components ────────────────────────────────────────────────────

def _render_user_bubble(turn: dict, i: int) -> None:
    with st.chat_message("user"):
        col_text, col_edit = st.columns([8, 1])
        with col_text:
            st.markdown(f"🎤 {turn['final_text']}")
        with col_edit:
            if st.button("✏️", key=f"edit_turn_{i}", help="Edit & resubmit"):
                turn["_editing"] = True
                st.rerun()


def _render_edit_form(turn: dict, i: int, t: dict) -> None:
    new_text = st.text_input(
        "Edit transcript", value=turn["final_text"], key=f"edit_input_{i}",
    )
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("↩ Resubmit", key=f"resubmit_{i}", type="primary"):
            turn["final_text"] = new_text
            turn["_editing"]   = False
            _resubmit(new_text, t)
    with col_cancel:
        if st.button("Cancel", key=f"cancel_edit_{i}"):
            turn["_editing"] = False
            st.rerun()


def _render_assistant_bubble(turn: dict) -> None:
    with st.chat_message("assistant"):
        st.markdown(turn["response_text"])
        lm = turn.get("latency_ms", {})
        if lm:
            stt = lm.get("stt", 0)
            llm = lm.get("llm", 0)
            st.caption(f"STT {stt:.0f} ms · LLM {llm:.0f} ms")


def _render_history(t: dict) -> None:
    turns = _vs()["turns"]
    if not turns:
        st.caption("No voice turns yet — tap the button below to start.")
        return
    for i, turn in enumerate(turns):
        if turn.get("final_text"):
            _render_user_bubble(turn, i)
        if turn.get("_editing"):
            _render_edit_form(turn, i, t)
        if turn.get("response_text"):
            _render_assistant_bubble(turn)


# ── Confirmation card ─────────────────────────────────────────────────────────

def _confirmation_card(turn: dict, t: dict) -> None:
    suggestion = (
        turn.get("suggested_confirmation")
        or f'Did you say "{turn.get("transcription_text", "…")}"?'
    )
    st.markdown(
        f'<div class="rm-confirm-card">'
        f'<div class="rm-confirm-q">🤔 {suggestion}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✓ Yes, that's right", key="confirm_yes",
                     type="primary", use_container_width=True):
            _confirm_and_send(turn.get("transcription_text", ""), t)
    with col_no:
        if st.button("✗ No, discard", key="confirm_no", use_container_width=True):
            _vs()["pending_confirmation"] = None
            st.rerun()


def _confirm_and_send(text: str, t: dict) -> None:
    from .api_client import api_post
    vs = _vs()
    with st.spinner(t.get("spinner_agent", "Thinking…")):
        try:
            res = api_post("/query/ask", {"question": text, "context_id": vs["context_id"]})
            vs["turns"].append({
                "final_text":    text,
                "response_text": res.get("answer", ""),
                "latency_ms":    {},
            })
            _browser_tts(res.get("answer", ""), vs.get("language") or "en")
        except Exception as e:
            st.error(f"Error: {e}")
    vs["pending_confirmation"] = None
    st.rerun()


# ── Resubmit edited transcript ────────────────────────────────────────────────

def _resubmit(text: str, t: dict) -> None:
    from .api_client import api_post
    vs = _vs()
    with st.spinner(t.get("spinner_agent", "Thinking…")):
        try:
            res = api_post("/query/ask", {"question": text, "context_id": vs["context_id"]})
            vs["turns"].append({
                "final_text":    text,
                "response_text": res.get("answer", ""),
                "latency_ms":    {},
            })
            _browser_tts(res.get("answer", ""), vs.get("language") or "en")
        except Exception as e:
            st.error(f"Error: {e}")
    st.rerun()


# ── TTS ───────────────────────────────────────────────────────────────────────

def _browser_tts(text: str, lang: str) -> None:
    """Speak via Web Speech API (free, no key, works offline)."""
    if not text:
        return
    lang_code = "pl-PL" if lang == "pl" else "en-US"
    safe = text[:600].replace('"', '\\"').replace("\n", " ")
    _components.html(
        f"""<script>
        const synth = window.parent.speechSynthesis;
        synth.cancel();
        const u = new SpeechSynthesisUtterance("{safe}");
        u.lang = "{lang_code}"; u.rate = 1.0;
        synth.speak(u);
        </script>""",
        height=0,
    )


# ── Mic + indicator section ───────────────────────────────────────────────────

def _mic_section(t: dict) -> None:
    vs  = _vs()
    status = vs.get("status", "idle")

    # Animated circle (class updated by JS for listening state)
    ind_class = "rm-voice-ind-processing" if status == "processing" else "rm-voice-ind-idle"
    st.markdown(
        f'<div id="rm-voice-ind" class="rm-voice-ind {ind_class}"></div>'
        '<div class="rm-vol-wrap"><div id="rm-vol-bar" class="rm-vol-bar"></div></div>'
        f'<p class="rm-voice-status">{_STATUS_TEXT.get(status, "Tap to speak")}</p>',
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 3, 1])
    with col:
        audio = mic_recorder(
            start_prompt="🎤  Tap to speak",
            stop_prompt="⏹  Stop recording",
            just_once=True,
            use_container_width=True,
            key=f"voice_mic_{vs['rec_n']}",
        )

    if audio and audio.get("bytes"):
        vs["status"] = "processing"
        vs["rec_n"] += 1
        _process_audio(audio["bytes"], t)


def _process_audio(audio_bytes: bytes, t: dict) -> None:
    vs = _vs()
    files = {
        "file":       ("voice.webm", audio_bytes, "audio/webm"),
        "context_id": (None, vs["context_id"] or ""),
        "language":   (None, vs["language"] or ""),
    }
    with st.spinner("Processing your voice…"):
        try:
            result = api_post_audio("/voice/turn", files=files)
        except Exception as exc:
            st.error(f"Voice processing error: {exc}")
            vs["status"] = "idle"
            st.rerun()
            return

    vs["status"] = "idle"
    decision = result.get("gate_decision")

    if decision in (None, _GATE_HALLUCINATION, _GATE_EMPTY):
        pass  # silent discard
    elif decision == _GATE_LIKELY_NOISE:
        st.toast("Didn't catch that — please try again.", icon="🔇")
    elif decision == _GATE_LOW_CONFIDENCE:
        vs["pending_confirmation"] = result
    elif decision == _GATE_VALID:
        vs["turns"].append(result)
        _browser_tts(result.get("response_text", ""), vs.get("language") or "en")

    st.rerun()


# ── Main page ─────────────────────────────────────────────────────────────────

def voice_mode_page(t: dict, context_id: str | None = None) -> None:
    """Render the full voice mode UI."""
    _init(context_id)
    _inject_voice_ui()
    vs = _vs()

    # ── Header ────────────────────────────────────────────────────────────────
    col_back, col_title = st.columns([2, 6])
    with col_back:
        if st.button("← Type instead", key="voice_type_instead"):
            st.session_state.pop("voice_state", None)
            st.rerun()
    with col_title:
        st.markdown("#### 🎤 Voice Mode")

    # ── Settings ──────────────────────────────────────────────────────────────
    with st.expander("⚙️ Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            lang_label = st.selectbox(
                "Language", list(_LANGS.keys()),
                index=0 if vs["language"] is None else (
                    ["Auto", "English", "Polski"].index(
                        {"en": "English", "pl": "Polski"}.get(vs["language"], "Auto")
                    )
                ),
                key="voice_lang_select",
            )
            vs["language"] = _LANGS[lang_label]
        with col2:
            vs["tts_voice"] = st.selectbox(
                "TTS Voice", _VOICES,
                index=_VOICES.index(vs.get("tts_voice", "nova")),
                key="voice_tts_select",
            )

    st.divider()

    # ── History ───────────────────────────────────────────────────────────────
    _render_history(t)

    # ── Confirmation card ─────────────────────────────────────────────────────
    if vs.get("pending_confirmation"):
        _confirmation_card(vs["pending_confirmation"], t)
        st.divider()

    # ── Circle + volume bar + mic ─────────────────────────────────────────────
    _mic_section(t)
