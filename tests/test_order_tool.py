import re

from app.agent.tools.order_tool import generate_order_id


def test_order_id_uses_business_name_initials():
    order_id = generate_order_id("The Dessert Zone")
    assert order_id.startswith("TDZ-")


def test_order_id_matches_expected_format():
    order_id = generate_order_id("WarmOven")
    assert re.match(r"^[A-Z]+-[0-9A-F]{8}$", order_id)


def test_order_id_falls_back_when_name_has_no_letters():
    order_id = generate_order_id("123")
    assert order_id.startswith("ORD-")


def test_order_ids_are_unique():
    ids = {generate_order_id("Test") for _ in range(20)}
    assert len(ids) == 20
