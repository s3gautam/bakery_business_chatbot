import pytest

from app.agent.tools.order_confirmation_tool import (
    OrderConfirmationTool,
    build_order_summary_email,
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


def _customer_details(**overrides) -> dict:
    defaults = dict(
        name="Asha", phone="9999999999", email="asha@example.com", address="123 Main St"
    )
    defaults.update(overrides)
    return defaults


class _RecordingEmailService:
    def __init__(self, fail_for: set[str] | None = None) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self._fail_for = fail_for or set()

    async def send(self, to_address: str, subject: str, body: str) -> None:
        if to_address in self._fail_for:
            raise RuntimeError("SMTP down")
        self.sent.append((to_address, subject, body))


def test_build_order_summary_email_includes_key_details():
    cart = [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 2}]
    subject, body = build_order_summary_email(
        "TB-ABC123", cart, _customer_details(), "2PM-3PM", _business_config()
    )
    assert "TB-ABC123" in subject
    assert "Test Bakery" in subject
    assert "Asha" in body
    assert "9999999999" in body
    assert "asha@example.com" in body
    assert "123 Main St" in body
    assert "Chocolate Cake" in body
    assert "2PM-3PM" in body
    assert "Paid" in body


def test_build_order_summary_email_includes_maps_link_when_present():
    _, body = build_order_summary_email(
        "TB-ABC123",
        [],
        _customer_details(maps_link="https://maps.google.com/xyz"),
        "2PM-3PM",
        _business_config(),
    )
    assert "https://maps.google.com/xyz" in body


def test_build_order_summary_email_omits_maps_link_when_absent():
    _, body = build_order_summary_email(
        "TB-ABC123", [], _customer_details(), "2PM-3PM", _business_config()
    )
    assert "Maps Link" not in body


@pytest.mark.asyncio
async def test_send_emails_both_admin_and_customer():
    email_service = _RecordingEmailService()
    tool = OrderConfirmationTool(email_service, "admin@bakery.com")
    cart = [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 1}]

    await tool.send("TB-ABC123", cart, _customer_details(), "2PM-3PM", _business_config())

    recipients = [to for to, _, _ in email_service.sent]
    assert "admin@bakery.com" in recipients
    assert "asha@example.com" in recipients
    assert len(email_service.sent) == 2


@pytest.mark.asyncio
async def test_send_skips_customer_email_when_missing():
    email_service = _RecordingEmailService()
    tool = OrderConfirmationTool(email_service, "admin@bakery.com")

    await tool.send(
        "TB-ABC123", [], _customer_details(email=""), "2PM-3PM", _business_config()
    )

    recipients = [to for to, _, _ in email_service.sent]
    assert recipients == ["admin@bakery.com"]


@pytest.mark.asyncio
async def test_send_continues_to_other_recipient_if_one_fails():
    email_service = _RecordingEmailService(fail_for={"admin@bakery.com"})
    tool = OrderConfirmationTool(email_service, "admin@bakery.com")

    await tool.send("TB-ABC123", [], _customer_details(), "2PM-3PM", _business_config())

    recipients = [to for to, _, _ in email_service.sent]
    assert recipients == ["asha@example.com"]
