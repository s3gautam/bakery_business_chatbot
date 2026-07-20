import json

import pytest

from app.agent.tools.payment_tool import PaymentTool
from app.store.models import BusinessConfig


def _business_config(**overrides) -> BusinessConfig:
    defaults = dict(
        business_name="Test Bakery",
        menu_source_url="https://www.swiggy.com/x",
        min_cart_for_free_delivery=300.0,
        free_delivery_radius_km=7.0,
        delivery_time_minutes=120,
        discount_percent=25.0,
        payment_phone_number="7479219293",
        payment_upi_id="7479219293@paytm",
        delivery_fee=75.0,
        accepted_receiver_names="Kouzina Kafe, Seema Gautam",
        extra_instructions=None,
    )
    defaults.update(overrides)
    return BusinessConfig(**defaults)


class _StubLLMService:
    def __init__(self, response: str) -> None:
        self._response = response

    async def complete_with_image(self, *args, **kwargs) -> str:
        return self._response


def _stub_response(**fields) -> str:
    defaults = dict(
        receiver_name="Kouzina Kafe",
        receiver_phone_or_upi="7479219293",
        amount=500,
        status="success",
    )
    defaults.update(fields)
    return json.dumps(defaults)


@pytest.mark.asyncio
async def test_validates_successful_payment_to_configured_number():
    tool = PaymentTool(_StubLLMService(_stub_response()))
    result = await tool.validate("fake-b64", _business_config())
    assert result.is_valid is True


@pytest.mark.asyncio
async def test_validates_successful_payment_to_configured_upi():
    tool = PaymentTool(
        _StubLLMService(_stub_response(receiver_phone_or_upi="7479219293@paytm"))
    )
    result = await tool.validate("fake-b64", _business_config())
    assert result.is_valid is True


@pytest.mark.asyncio
async def test_rejects_wrong_receiver_name():
    tool = PaymentTool(_StubLLMService(_stub_response(receiver_name="Someone Else")))
    result = await tool.validate("fake-b64", _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_rejects_wrong_receiver_number():
    tool = PaymentTool(_StubLLMService(_stub_response(receiver_phone_or_upi="9999999999")))
    result = await tool.validate("fake-b64", _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_rejects_non_success_status():
    tool = PaymentTool(_StubLLMService(_stub_response(status="pending")))
    result = await tool.validate("fake-b64", _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_rejects_unparseable_response():
    tool = PaymentTool(_StubLLMService("not json"))
    result = await tool.validate("fake-b64", _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_accepts_any_configured_receiver_name():
    tool = PaymentTool(_StubLLMService(_stub_response(receiver_name="Seema Gautam")))
    result = await tool.validate("fake-b64", _business_config())
    assert result.is_valid is True
