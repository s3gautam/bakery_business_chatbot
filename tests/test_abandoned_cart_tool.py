import pytest

from app.agent.tools.abandoned_cart_tool import (
    AbandonedCartReminderTool,
    build_abandoned_cart_email,
)
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


def _cart() -> list[dict]:
    return [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 1}]


class _RecordingEmailService:
    def __init__(self, fail: bool = False) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self._fail = fail

    async def send(self, to_address: str, subject: str, body: str) -> None:
        if self._fail:
            raise RuntimeError("SMTP down")
        self.sent.append((to_address, subject, body))


def test_build_email_includes_cart_and_call_number():
    subject, body = build_abandoned_cart_email(
        _cart(), {"name": "Asha", "email": "asha@example.com"}, _business_config()
    )
    assert "Test Bakery" in subject
    assert "Asha" in body
    assert "Chocolate Cake" in body
    assert "7479219293" in body


def test_build_email_uses_generic_greeting_without_name():
    _, body = build_abandoned_cart_email(_cart(), {"email": "a@b.com"}, _business_config())
    assert body.startswith("Hi,")


@pytest.mark.asyncio
async def test_send_emails_customer_when_email_known():
    email_service = _RecordingEmailService()
    tool = AbandonedCartReminderTool(email_service)

    sent = await tool.send(_cart(), {"email": "asha@example.com"}, _business_config())

    assert sent is True
    assert len(email_service.sent) == 1
    assert email_service.sent[0][0] == "asha@example.com"


@pytest.mark.asyncio
async def test_send_does_nothing_without_email():
    email_service = _RecordingEmailService()
    tool = AbandonedCartReminderTool(email_service)

    sent = await tool.send(_cart(), {}, _business_config())

    assert sent is False
    assert email_service.sent == []


@pytest.mark.asyncio
async def test_send_does_nothing_for_empty_cart():
    email_service = _RecordingEmailService()
    tool = AbandonedCartReminderTool(email_service)

    sent = await tool.send([], {"email": "asha@example.com"}, _business_config())

    assert sent is False
    assert email_service.sent == []


@pytest.mark.asyncio
async def test_send_returns_false_on_email_failure():
    email_service = _RecordingEmailService(fail=True)
    tool = AbandonedCartReminderTool(email_service)

    sent = await tool.send(_cart(), {"email": "asha@example.com"}, _business_config())

    assert sent is False
