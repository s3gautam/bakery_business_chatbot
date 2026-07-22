import pytest

from app.services.language import LanguageDetectionService, detect_language_heuristic


def test_detects_hindi_devanagari_script():
    assert detect_language_heuristic("मुझे केक चाहिए") == "hi"


def test_detects_hinglish_by_keyword():
    assert detect_language_heuristic("cake ka price kya hai") == "hinglish"


def test_returns_none_for_plain_english():
    assert detect_language_heuristic("What cakes do you have?") is None


def test_returns_none_for_ambiguous_short_text():
    assert detect_language_heuristic("menu") is None


class _ExplodingLLMService:
    """The service must never call the LLM to guess a language — this
    stub blows up if it's ever invoked."""

    async def complete(self, *args, **kwargs):
        raise AssertionError("LanguageDetectionService should never call the LLM")


@pytest.mark.asyncio
async def test_detect_never_calls_llm_and_defaults_to_english():
    service = LanguageDetectionService(_ExplodingLLMService())
    result = await service.detect("siddhant 7015943285 gsiddhant@gmail.com address: gurgaon")
    assert result == "en"


@pytest.mark.asyncio
async def test_detect_is_sticky_to_previous_language_when_ambiguous():
    service = LanguageDetectionService(_ExplodingLLMService())
    result = await service.detect("ok", previous_language="hinglish")
    assert result == "hinglish"


@pytest.mark.asyncio
async def test_detect_switches_on_clear_signal_even_with_prior_language():
    service = LanguageDetectionService(_ExplodingLLMService())
    result = await service.detect("मुझे केक चाहिए", previous_language="en")
    assert result == "hi"
