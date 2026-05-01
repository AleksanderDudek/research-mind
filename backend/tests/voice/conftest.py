"""Shared fixtures for voice tests."""
import os
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ── Audio fixture loader ───────────────────────────────────────────────────────

def _fixture_path(name: str) -> Path:
    return FIXTURES_DIR / name


def require_fixture(name: str):
    """Return path to an audio fixture, skipping the test if the file is absent."""
    p = _fixture_path(name)
    if not p.exists():
        pytest.skip(f"Audio fixture '{name}' not present — add it to tests/voice/fixtures/")
    return p


# ── Convenience fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def silence_path():
    return require_fixture("silence_3s.wav")


@pytest.fixture
def clear_speech_path():
    return require_fixture("clear_speech.wav")


@pytest.fixture
def noisy_speech_path():
    return require_fixture("noisy_speech.wav")


@pytest.fixture
def mumbled_path():
    return require_fixture("mumbled.wav")


@pytest.fixture
def single_yes_path():
    return require_fixture("single_yes.wav")


@pytest.fixture
def polish_question_path():
    return require_fixture("polish_question.wav")
