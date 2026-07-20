import base64
import json

import pytest

from app.agent.tools.payment_tool import PaymentTool
from app.config import get_settings
from app.store.models import BusinessConfig

_FAKE_IMAGE_B64 = base64.b64encode(b"not a real image").decode("ascii")


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

    async def complete(self, *args, **kwargs) -> str:
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


def _tool(llm_response: str, ocr_text: str = "some ocr text") -> PaymentTool:
    return PaymentTool(
        _StubLLMService(llm_response), get_settings(), ocr_extract=lambda _: ocr_text
    )


@pytest.mark.asyncio
async def test_validates_successful_payment_to_configured_number():
    tool = _tool(_stub_response())
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is True


@pytest.mark.asyncio
async def test_validates_successful_payment_to_configured_upi():
    tool = _tool(_stub_response(receiver_phone_or_upi="7479219293@paytm"))
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is True


@pytest.mark.asyncio
async def test_rejects_wrong_receiver_name():
    tool = _tool(_stub_response(receiver_name="Someone Else"))
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_rejects_wrong_receiver_number():
    tool = _tool(_stub_response(receiver_phone_or_upi="9999999999"))
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_rejects_non_success_status():
    tool = _tool(_stub_response(status="pending"))
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_rejects_unparseable_response():
    tool = _tool("not json")
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_accepts_any_configured_receiver_name():
    tool = _tool(_stub_response(receiver_name="Seema Gautam"))
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is True


@pytest.mark.asyncio
async def test_rejects_when_ocr_extracts_no_text():
    tool = _tool(_stub_response(), ocr_text="   ")
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is False
    assert "clearer image" in result.reason


@pytest.mark.asyncio
async def test_rejects_when_ocr_raises():
    def _broken_ocr(_: bytes) -> str:
        raise RuntimeError("tesseract not installed")

    tool = PaymentTool(_StubLLMService(_stub_response()), get_settings(), ocr_extract=_broken_ocr)
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is False


@pytest.mark.asyncio
async def test_real_world_negative_case_wrong_receiver_direction():
    """Regression test from a real screenshot: money paid OUT from the
    business account to a third party ('Crembow') — the OCR captured the
    payer ('Kouzina Kafe') and payee names in the same document, and the
    extraction must not be fooled into treating the payer as the payee.
    """
    ocr_text = (
        "Paytm\nCrembow\ncrembow@ibl on PhonePe\n₹750\n"
        "Seven Hundred Fifty Rupees\nPaid Successfully\n"
        "From\nKouzina Kafe\nIDFC FIRST Bank - 1111\n"
        "18 Jul, 05:26 PM | Ref No: 2110 9140 4723"
    )
    tool = _tool(
        _stub_response(receiver_name="Crembow", receiver_phone_or_upi="crembow@ibl"),
        ocr_text=ocr_text,
    )
    result = await tool.validate(_FAKE_IMAGE_B64, _business_config())
    assert result.is_valid is False
    assert result.receiver_name == "Crembow"
