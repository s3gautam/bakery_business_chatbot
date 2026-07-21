import json

import pytest

from app.agent.nlu import NLUService
from app.store.models import BusinessConfig


def _business_config() -> BusinessConfig:
    return BusinessConfig(
        business_name="Test Bakery",
        menu_source_url="https://www.swiggy.com/x",
        min_cart_for_free_delivery=300.0,
        free_delivery_radius_km=7.0,
        delivery_time_minutes=120,
        discount_percent=25.0,
        payment_phone_number="7479219293",
        payment_upi_id="7479219293@paytm",
        delivery_fee=75.0,
        accepted_receiver_names="Kouzina Kafe",
        extra_instructions=None,
    )


class _RecordingLLMService:
    def __init__(self, response: str) -> None:
        self._response = response
        self.last_messages = None

    async def complete(self, messages, **kwargs) -> str:
        self.last_messages = messages
        return self._response


@pytest.mark.asyncio
async def test_classify_includes_history_messages_before_current_turn():
    llm = _RecordingLLMService(json.dumps({"intent": "cart_add", "cart_item_name": "x"}))
    service = NLUService(llm)
    history = [
        {"role": "user", "content": "what's the price of the chocolate jar cake?"},
        {"role": "assistant", "content": "It's Rs. 300."},
    ]

    await service.classify("yes add 1", _business_config(), history=history)

    roles_and_content = [(m["role"], m["content"]) for m in llm.last_messages]
    assert ("user", "what's the price of the chocolate jar cake?") in roles_and_content
    assert ("assistant", "It's Rs. 300.") in roles_and_content
    assert roles_and_content[-1] == ("user", "yes add 1")


@pytest.mark.asyncio
async def test_classify_works_without_history():
    llm = _RecordingLLMService(json.dumps({"intent": "menu_query"}))
    service = NLUService(llm)

    result = await service.classify("what do you have?", _business_config())

    assert result.intent == "menu_query"
    assert len(llm.last_messages) == 2  # system + current message only


@pytest.mark.asyncio
async def test_classify_requests_json_mode():
    llm = _RecordingLLMService(json.dumps({"intent": "cart_add", "cart_item_name": "x"}))
    service = NLUService(llm)
    llm.complete = None  # ensure we inspect kwargs via a wrapper below

    calls = {}

    async def _complete(messages, **kwargs):
        calls.update(kwargs)
        return json.dumps({"intent": "cart_add", "cart_item_name": "x"})

    llm.complete = _complete
    await service.classify("add 1 red velvet cake to cart", _business_config())

    assert calls.get("json_mode") is True


@pytest.mark.asyncio
async def test_classify_strips_markdown_fenced_json():
    llm = _RecordingLLMService(
        "```json\n" + json.dumps({"intent": "cart_add", "cart_item_name": "Red Velvet"}) + "\n```"
    )
    service = NLUService(llm)

    result = await service.classify("add 1 red velvet cake to cart", _business_config())

    assert result.intent == "cart_add"
    assert result.cart_item_name == "Red Velvet"


@pytest.mark.asyncio
async def test_classify_caps_history_length():
    llm = _RecordingLLMService(json.dumps({"intent": "general"}))
    service = NLUService(llm)
    long_history = [{"role": "user", "content": f"msg {i}"} for i in range(20)]

    await service.classify("hello", _business_config(), history=long_history)

    # system prompt + at most 6 history turns + current message
    assert len(llm.last_messages) <= 8
