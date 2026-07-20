import json
from dataclasses import dataclass

from app.agent.prompts import build_nlu_system_prompt
from app.agent.state import Intent
from app.services.llm import LLMService
from app.store.models import BusinessConfig

_VALID_INTENTS = {
    "menu_query",
    "feedback",
    "order_request",
    "custom_cake_request",
    "bulk_order_request",
    "general",
}

_VALID_PLATFORMS = {"swiggy", "zomato", "other"}


@dataclass(frozen=True)
class NLUResult:
    intent: Intent
    search_query: str | None
    order_id: str | None
    platform: str | None
    feedback_message: str | None


def _safe_platform(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    label = raw.lower()
    return label if label in _VALID_PLATFORMS else None


class NLUService:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def classify(self, message: str, business_config: BusinessConfig) -> NLUResult:
        raw = await self._llm_service.complete(
            messages=[
                {"role": "system", "content": build_nlu_system_prompt(business_config)},
                {"role": "user", "content": message},
            ],
            temperature=0.0,
            max_tokens=300,
        )

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            data = {}

        intent = data.get("intent")
        if intent not in _VALID_INTENTS:
            intent = "general"

        return NLUResult(
            intent=intent,
            search_query=data.get("search_query"),
            order_id=data.get("order_id"),
            platform=_safe_platform(data.get("platform")),
            feedback_message=data.get("feedback_message"),
        )
