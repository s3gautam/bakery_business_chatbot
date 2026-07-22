import re

from app.services.llm import LLMService

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# Common Hinglish (Romanized Hindi) tokens. Not exhaustive by design —
# text with no Devanagari and none of these tokens is treated as not
# having a clear non-English signal (see LanguageDetectionService).
_HINGLISH_TOKENS = {
    "hai", "haan", "nahi", "nahin", "kya", "kaise", "kitna", "kitne",
    "aap", "aapka", "chahiye", "milega", "kab", "kaha", "kahan", "bhai",
    "acha", "theek", "matlab", "bhi", "abhi", "batao", "keemat", "daam",
}

_SUPPORTED_LANGUAGES = {"en", "hi", "hinglish"}


def detect_language_heuristic(text: str) -> str | None:
    """Fast, deterministic detection for unambiguous cases.

    Returns None when there's no clear signal either way.
    """
    if _DEVANAGARI_RE.search(text):
        return "hi"

    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    if tokens & _HINGLISH_TOKENS:
        return "hinglish"

    return None


class LanguageDetectionService:
    """Detects the customer's language from clear, deterministic signals
    only (Devanagari script, or well-known Hinglish tokens). Deliberately
    does NOT ask an LLM to guess the language of ambiguous, short, or
    English-looking text (e.g. a name/phone/email/address block) — an
    LLM misclassifying that as Hindi would silently flip every reply
    into Hindi for a customer who never asked for it. When there's no
    clear signal, the conversation's language stays whatever it already
    was (sticky), defaulting to English at the start of a conversation.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def detect(self, text: str, previous_language: str = "en") -> str:
        heuristic_result = detect_language_heuristic(text)
        if heuristic_result is not None:
            return heuristic_result
        return previous_language if previous_language in _SUPPORTED_LANGUAGES else "en"
