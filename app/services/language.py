import re

from app.services.llm import LLMService

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# Common Hinglish (Romanized Hindi) tokens — a fast path so obvious cases
# skip the LLM call. Not exhaustive: anything not caught here still goes
# to the LLM classifier below, which judges actual meaning rather than a
# fixed word list.
_HINGLISH_TOKENS = {
    "hai", "haan", "nahi", "nahin", "kya", "kaise", "kitna", "kitne",
    "aap", "aapka", "chahiye", "milega", "kab", "kaha", "kahan", "bhai",
    "acha", "theek", "matlab", "bhi", "abhi", "batao", "keemat", "daam",
}

_SUPPORTED_LANGUAGES = {"en", "hi", "hinglish"}

# Matches contact/address details a customer types when asked for their
# name/phone/email/delivery address — these are proper nouns, digits, and
# place names, not conversational language, and must never influence
# language detection (a city name like "Gurgaon" isn't a Hindi signal).
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s]{6,}\d)")
_ADDRESS_LABEL_RE = re.compile(
    r"\b(name|phone|email|address|pin\s*code|pincode)\s*[:\-]?\s*", re.IGNORECASE
)

_CLASSIFIER_SYSTEM_PROMPT = (
    "You are a language classifier for a bakery chatbot. Classify the "
    "customer's message into exactly one of: en, hi, hinglish. "
    "'hinglish' means Hindi written in Latin/Roman script, optionally "
    "mixed with English words. Reply with only the label, nothing else."
)


def _contains_contact_details(text: str) -> bool:
    """True if the message contains an email, a phone-number-shaped
    digit run, or an explicit name/phone/email/address field label. Any
    of these means this turn is (at least partly) a customer-details
    submission, so the whole message — including any name/city words
    sitting next to those details — must never be used for language
    detection (see LanguageDetectionService).
    """
    return bool(_EMAIL_RE.search(text) or _PHONE_RE.search(text) or _ADDRESS_LABEL_RE.search(text))


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
    """Detects the customer's language from what they actually wrote —
    not just script or a fixed keyword list, via an LLM classifier that
    judges real meaning. Any message containing an email, phone number,
    or a name/phone/email/address field label is treated as a customer-
    details submission and is never used for detection at all — not
    even the name/city words sitting next to those details — since
    those are proper nouns, not conversational language, and previously
    caused a false "switch to Hindi" (e.g. "siddhant 7015943285
    x@gmail.com address: gurgaon"). In that case, and whenever detection
    is otherwise ambiguous, the conversation's language stays whatever
    it already was (sticky), defaulting to English at the start.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def detect(self, text: str, previous_language: str = "en") -> str:
        default = previous_language if previous_language in _SUPPORTED_LANGUAGES else "en"

        if _contains_contact_details(text):
            return default

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
        return label if label in _SUPPORTED_LANGUAGES else default
