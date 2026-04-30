"""Unit tests for the quality gate heuristics + LLM arbiter (mocked)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.voice.schemas import GateDecision, TranscriptionResult, TranscriptionSegment


def _make_result(
    text: str = "hello world",
    language: str = "en",
    duration_s: float = 2.0,
    no_speech_prob: float = 0.05,
    avg_logprob: float = -0.2,
    compression_ratio: float = 1.2,
    word_count: int | None = None,
) -> TranscriptionResult:
    if word_count is None:
        word_count = len(text.split())
    seg = TranscriptionSegment(
        start=0.0, end=duration_s, text=text,
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        compression_ratio=compression_ratio,
    )
    return TranscriptionResult(
        text=text, language=language,
        duration_s=duration_s, segments=[seg],
        word_count=word_count,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_empty_text():
    from app.voice.quality_gate import evaluate
    result = _make_result(text="   ", word_count=0)
    gate = evaluate(result)
    assert gate.decision == GateDecision.EMPTY


def test_clean_speech_is_valid():
    from app.voice.quality_gate import evaluate
    result = _make_result(text="What is RAG?", no_speech_prob=0.05, avg_logprob=-0.2)
    gate = evaluate(result)
    assert gate.decision == GateDecision.VALID


def test_all_silence_is_noise():
    from app.voice.quality_gate import evaluate
    result = _make_result(text="thank you", no_speech_prob=0.95, avg_logprob=-2.5)
    gate = evaluate(result)
    assert gate.decision in (GateDecision.LIKELY_NOISE, GateDecision.HALLUCINATION)


def test_hallucination_text():
    from app.voice.quality_gate import evaluate
    result = _make_result(text="Thanks for watching.", no_speech_prob=0.7, avg_logprob=-2.0)
    gate = evaluate(result)
    assert gate.decision == GateDecision.HALLUCINATION


def test_borderline_low_confidence():
    from app.voice.quality_gate import evaluate
    # Single word, borderline logprob
    result = _make_result(text="maybe", duration_s=0.8, avg_logprob=-0.8, word_count=1)
    gate = evaluate(result)
    assert gate.decision in (GateDecision.LOW_CONFIDENCE, GateDecision.LIKELY_NOISE)
    if gate.decision == GateDecision.LOW_CONFIDENCE:
        assert gate.suggested_confirmation is not None


def test_word_rate_too_high():
    from app.voice.quality_gate import evaluate
    # 8 words in 0.5 s = 16 wps >> max 5 wps → noise
    result = _make_result(
        text="one two three four five six seven eight",
        duration_s=0.5, word_count=8,
        no_speech_prob=0.1, avg_logprob=-0.3,
    )
    gate = evaluate(result)
    assert gate.decision == GateDecision.LIKELY_NOISE


# ── LLM arbiter tests (mocked) ────────────────────────────────────────────────

def _lc_result():
    """A result that the heuristic classifies as LOW_CONFIDENCE."""
    return _make_result(text="maybe", duration_s=0.8, avg_logprob=-0.8, word_count=1)


def _mock_openai_response(coherent: bool) -> MagicMock:
    """Build a minimal mock that looks like an OpenAI chat completion."""
    msg  = MagicMock()
    msg.content = f'{{"coherent": {"true" if coherent else "false"}, "reason": "test"}}'
    choice = MagicMock()
    choice.choices = [MagicMock(message=msg)]
    return choice


@pytest.mark.asyncio
async def test_arbiter_promotes_low_confidence_to_valid():
    """Arbiter says coherent=true → LOW_CONFIDENCE becomes VALID."""
    from app.voice.quality_gate import evaluate_with_arbiter

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(coherent=True)
    )

    with patch("app.llm.client.LLMClient.get", return_value=mock_client):
        gate = await evaluate_with_arbiter(_lc_result())

    assert gate.decision == GateDecision.VALID
    assert "arbiter override" in gate.reasons


@pytest.mark.asyncio
async def test_arbiter_demotes_low_confidence_to_noise():
    """Arbiter says coherent=false → LOW_CONFIDENCE becomes LIKELY_NOISE."""
    from app.voice.quality_gate import evaluate_with_arbiter

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(coherent=False)
    )

    with patch("app.llm.client.LLMClient.get", return_value=mock_client):
        gate = await evaluate_with_arbiter(_lc_result())

    assert gate.decision == GateDecision.LIKELY_NOISE
    assert "arbiter override" in gate.reasons


@pytest.mark.asyncio
async def test_arbiter_failure_keeps_heuristic():
    """If all arbiter retries fail, heuristic LOW_CONFIDENCE is returned unchanged."""
    from app.voice.quality_gate import evaluate_with_arbiter

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("network error")
    )

    with patch("app.llm.client.LLMClient.get", return_value=mock_client):
        gate = await evaluate_with_arbiter(_lc_result())

    assert gate.decision == GateDecision.LOW_CONFIDENCE
    assert gate.suggested_confirmation is not None


@pytest.mark.asyncio
async def test_arbiter_skipped_for_valid():
    """Arbiter is never called when heuristic already yields VALID."""
    from app.voice.quality_gate import evaluate_with_arbiter

    mock_client = AsyncMock()

    result = _make_result(text="What is retrieval augmented generation?",
                          no_speech_prob=0.03, avg_logprob=-0.1)

    with patch("app.llm.client.LLMClient.get", return_value=mock_client):
        gate = await evaluate_with_arbiter(result)

    assert gate.decision == GateDecision.VALID
    mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_arbiter_disabled_by_flag():
    """Setting llm_arbiter_enabled=False prevents any arbiter call."""
    from app.voice import quality_gate
    from app.voice.quality_gate import evaluate_with_arbiter

    mock_client = AsyncMock()

    with (
        patch("app.llm.client.LLMClient.get", return_value=mock_client),
        patch.object(quality_gate.voice_settings, "llm_arbiter_enabled", False),
    ):
        gate = await evaluate_with_arbiter(_lc_result())

    assert gate.decision == GateDecision.LOW_CONFIDENCE
    mock_client.chat.completions.create.assert_not_called()
