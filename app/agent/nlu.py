import json
from dataclasses import dataclass

from app.agent.prompts import build_nlu_system_prompt
from app.agent.state import Intent
from app.services.llm import LLMService
from app.store.models import BusinessConfig

_VALID_INTENTS = {
    "menu_query",
    "feedback",
    "cart_add",
    "cart_remove",
    "cart_update",
    "cart_show",
    "cart_clear",
    "checkout",
    "provide_customer_details",
    "provide_delivery_slot",
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
    cart_item_name: str | None
    cart_quantity: int | None
    customer_name: str | None
    customer_phone: str | None
    customer_email: str | None
    customer_address: str | None
    maps_link: str | None
    delivery_slot_text: str | None


def _safe_platform(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    label = raw.lower()
    return label if label in _VALID_PLATFORMS else None


def _safe_int(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().lstrip("-").isdigit():
        return int(raw.strip())
    return None


class NLUService:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def classify(
        self,
        message: str,
        business_config: BusinessConfig,
        history: list[dict[str, str]] | None = None,
    ) -> NLUResult:
        messages = [{"role": "system", "content": build_nlu_system_prompt(business_config)}]
        for turn in (history or [])[-6:]:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        raw = await self._llm_service.complete(
            messages=messages,
            temperature=0.0,
            max_tokens=400,
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
            cart_item_name=data.get("cart_item_name"),
            cart_quantity=_safe_int(data.get("cart_quantity")),
            customer_name=data.get("customer_name"),
            customer_phone=data.get("customer_phone"),
            customer_email=data.get("customer_email"),
            customer_address=data.get("customer_address"),
            maps_link=data.get("maps_link"),
            delivery_slot_text=data.get("delivery_slot_text"),
        )
