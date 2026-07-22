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
    """Fails the test if the language classifier is ever called — used to
    prove contact-detail messages never reach the LLM."""

    async def complete(self, *args, **kwargs):
        raise AssertionError("LanguageDetectionService should not call the LLM here")


class _RecordingLLMService:
    def __init__(self, response: str) -> None:
        self._response = response
        self.called_with: list[dict] | None = None

    async def complete(self, messages, **kwargs) -> str:
        self.called_with = messages
        return self._response


@pytest.mark.asyncio
async def test_detect_skips_llm_for_message_with_email_and_phone():
    service = LanguageDetectionService(_ExplodingLLMService())
    result = await service.detect("siddhant 7015943285 gsiddhant@gmail.com address: gurgaon")
    assert result == "en"


@pytest.mark.asyncio
async def test_detect_skips_llm_and_stays_sticky_for_contact_details():
    service = LanguageDetectionService(_ExplodingLLMService())
    result = await service.detect(
        "siddhant 7015943285 gsiddhant@gmail.com address: gurgaon",
        previous_language="hinglish",
    )
    assert result == "hinglish"


@pytest.mark.asyncio
async def test_detect_skips_llm_for_address_label_alone():
    # No email/phone, but an explicit "address:" label is still contact
    # info (a city name shouldn't be read as a language signal).
    service = LanguageDetectionService(_ExplodingLLMService())
    result = await service.detect("address: gurgaon sector 49", previous_language="en")
    assert result == "en"


@pytest.mark.asyncio
async def test_detect_uses_llm_for_genuine_conversational_text():
    llm = _RecordingLLMService("hinglish")
    service = LanguageDetectionService(llm)

    result = await service.detect("cake bahut mast lagta")

    assert result == "hinglish"
    assert llm.called_with is not None


@pytest.mark.asyncio
async def test_detect_is_sticky_when_llm_returns_unsupported_label():
    llm = _RecordingLLMService("not-a-real-label")
    service = LanguageDetectionService(llm)

    result = await service.detect("some ambiguous text", previous_language="hinglish")

    assert result == "hinglish"


@pytest.mark.asyncio
async def test_detect_switches_on_devanagari_without_calling_llm():
    service = LanguageDetectionService(_ExplodingLLMService())
    result = await service.detect("मुझे केक चाहिए", previous_language="en")
    assert result == "hi"
