from app.agent.prompts import build_reply_system_prompt
from app.config import get_settings
from app.store.models import BusinessConfig


def _business_config(**overrides) -> BusinessConfig:
    defaults = dict(
        menu_source_url="https://www.swiggy.com/x",
        min_cart_for_free_delivery=300.0,
        free_delivery_radius_km=7.0,
        delivery_time_minutes=120,
        discount_percent=25.0,
        payment_phone_number="7479219293",
        payment_upi_id="7479219293@paytm",
        extra_instructions=None,
    )
    defaults.update(overrides)
    return BusinessConfig(**defaults)


def test_prompt_includes_configured_business_facts():
    prompt = build_reply_system_prompt(get_settings(), _business_config())
    assert "300.0" in prompt
    assert "7.0 km" in prompt
    assert "120" in prompt
    assert "25.0%" in prompt


def test_prompt_appends_extra_instructions_when_present():
    prompt = build_reply_system_prompt(
        get_settings(), _business_config(extra_instructions="Diwali sale this week.")
    )
    assert "Diwali sale this week." in prompt


def test_prompt_omits_extra_instructions_section_when_absent():
    prompt = build_reply_system_prompt(get_settings(), _business_config())
    assert "Additional instructions from the business owner" not in prompt
