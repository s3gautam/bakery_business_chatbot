import re

from app.services.llm import LLMService

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# Common Hinglish (Romanized Hindi) tokens used to short-circuit the LLM
# call for obvious cases. Not exhaustive by design — ambiguous input falls
# through to the LLM classifier.
_HINGLISH_TOKENS = {
    "hai", "haan", "nahi", "nahin", "kya", "kaise", "kitna", "kitne",
    "aap", "aapka", "chahiye", "milega", "kab", "kaha", "kahan", "bhai",
    "acha", "theek", "matlab", "bhi", "abhi", "batao", "keemat", "daam",
}

_SUPPORTED_LANGUAGES = {"en", "hi", "hinglish"}

_CLASSIFIER_SYSTEM_PROMPT = (
    "You are a language classifier for a bakery chatbot. Classify the "
    "customer's message into exactly one of: en, hi, hinglish. "
    "'hinglish' means Hindi written in Latin/Roman script, optionally "
    "mixed with English words. Reply with only the label, nothing else."
)


def detect_language_heuristic(text: str) -> str | None:
    """Fast, deterministic detection for unambiguous cases.

    Returns None when the LLM classifier should be used instead.
    """
    if _DEVANAGARI_RE.search(text):
        return "hi"

    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    if tokens & _HINGLISH_TOKENS:
        return "hinglish"

    return None


class LanguageDetectionService:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def detect(self, text: str) -> str:
        heuristic_result = detect_language_heuristic(text)
        if heuristic_result is not None:
            return heuristic_result

        raw_label = await self._llm_service.complete(
            messages=[
                {"role": "system", "content": _CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=5,
        )
        label = raw_label.strip().lower()
        return label if label in _SUPPORTED_LANGUAGES else "en"
