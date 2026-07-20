import base64
import json
import re
from dataclasses import dataclass
from typing import Callable

from app.config import Settings
from app.services.llm import LLMService
from app.services.ocr_service import extract_text
from app.store.models import BusinessConfig

_EXTRACTION_PROMPT_HEADER = """The following text was OCR'd from a payment \
screenshot (UPI/bank transfer app). OCR is imperfect — expect misread \
characters (e.g. "Payim" for "Paytm", "°" for "₹") and missing labels; \
use context to correct obvious OCR noise. Extract the payment details \
as strict JSON only, no prose, matching this schema:

{
  "receiver_name": string | null,
  "receiver_phone_or_upi": string | null,
  "amount": number | null,
  "status": "success" | "pending" | "failed" | "unclear"
}

Only fill fields you can confidently infer from the text. The receiver \
is whoever RECEIVED the money — pay close attention to labels like "To"/
"From"/"Paid to" to get the direction right; do not assume the first \
name in the text is the receiver. If you cannot confidently read a \
field, use null.

OCR text:
---
"""


def _build_extraction_prompt(ocr_text: str) -> str:
    # Deliberately not str.format()/f-string here — the header above
    # contains literal {..} JSON braces that would collide with format
    # placeholders.
    return f"{_EXTRACTION_PROMPT_HEADER}{ocr_text}\n---\n"


@dataclass(frozen=True)
class PaymentValidationResult:
    is_valid: bool
    reason: str
    receiver_name: str | None
    receiver_identifier: str | None
    amount: float | None


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9@.]", "", value.lower())


def _name_matches(extracted_name: str | None, accepted_names: list[str]) -> bool:
    if not extracted_name:
        return False
    extracted = extracted_name.strip().lower()
    return any(extracted == name.strip().lower() for name in accepted_names)


class PaymentTool:
    """Agent tool: validates a payment screenshot via Tesseract OCR
    followed by a single fast text-LLM call to structure the OCR'd text
    into JSON (no vision model). Only accepts screenshots that clearly
    show a successful payment to one of the configured receiver numbers/
    UPI IDs under an accepted receiver name. Never approves an uncertain
    screenshot.
    """

    def __init__(
        self,
        llm_service: LLMService,
        settings: Settings,
        ocr_extract: Callable[[bytes], str] = extract_text,
    ) -> None:
        self._llm_service = llm_service
        self._settings = settings
        self._ocr_extract = ocr_extract

    async def validate(
        self, image_b64: str, business_config: BusinessConfig, image_mime_type: str = "image/png"
    ) -> PaymentValidationResult:
        try:
            image_bytes = base64.b64decode(image_b64)
            ocr_text = self._ocr_extract(image_bytes)
        except Exception:
            return PaymentValidationResult(
                is_valid=False,
                reason="Could not read the screenshot. Please retry with a clearer image.",
                receiver_name=None,
                receiver_identifier=None,
                amount=None,
            )

        if not ocr_text.strip():
            return PaymentValidationResult(
                is_valid=False,
                reason="Could not read any text from the screenshot. Please retry with a clearer image.",
                receiver_name=None,
                receiver_identifier=None,
                amount=None,
            )

        try:
            raw = await self._llm_service.complete(
                messages=[
                    {
                        "role": "system",
                        "content": _build_extraction_prompt(ocr_text),
                    }
                ],
                temperature=0.0,
                max_tokens=300,
                model=self._settings.groq_instant_model,
            )
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return PaymentValidationResult(
                is_valid=False,
                reason="Could not read the screenshot clearly. Please retry with a clearer image.",
                receiver_name=None,
                receiver_identifier=None,
                amount=None,
            )
        except Exception:
            return PaymentValidationResult(
                is_valid=False,
                reason="We couldn't process that screenshot right now. Please retry.",
                receiver_name=None,
                receiver_identifier=None,
                amount=None,
            )

        receiver_name = data.get("receiver_name")
        receiver_identifier = data.get("receiver_phone_or_upi")
        amount = data.get("amount")
        status = data.get("status")

        if status != "success":
            return PaymentValidationResult(
                is_valid=False,
                reason="The screenshot doesn't clearly show a successful payment.",
                receiver_name=receiver_name,
                receiver_identifier=receiver_identifier,
                amount=amount,
            )

        if not _name_matches(receiver_name, business_config.accepted_receiver_names_list):
            return PaymentValidationResult(
                is_valid=False,
                reason="The receiver name on the screenshot doesn't match our account.",
                receiver_name=receiver_name,
                receiver_identifier=receiver_identifier,
                amount=amount,
            )

        expected_identifiers = {
            _normalize_identifier(business_config.payment_phone_number),
            _normalize_identifier(business_config.payment_upi_id),
        }
        if not receiver_identifier or _normalize_identifier(receiver_identifier) not in expected_identifiers:
            return PaymentValidationResult(
                is_valid=False,
                reason="The receiver phone number/UPI on the screenshot doesn't match ours.",
                receiver_name=receiver_name,
                receiver_identifier=receiver_identifier,
                amount=amount,
            )

        return PaymentValidationResult(
            is_valid=True,
            reason="Payment validated.",
            receiver_name=receiver_name,
            receiver_identifier=receiver_identifier,
            amount=amount,
        )
