from app.agent.tools.cart_tool import CartTool, compute_totals, format_cart
from app.config import get_settings
from app.store.menu_store import MenuStore
from app.store.models import BusinessConfig, MenuItem


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
        accepted_receiver_names="Kouzina Kafe",
        extra_instructions=None,
    )
    defaults.update(overrides)
    return BusinessConfig(**defaults)


def _cart_tool(tmp_path) -> CartTool:
    settings = get_settings().model_copy(update={"menu_file_path": tmp_path / "menu.json"})
    store = MenuStore(settings)
    store.save_all(
        [
            MenuItem("Chocolate Cake", None, 500.0, "Chocolate", None, True),
            MenuItem("Red Velvet Cake", None, 100.0, "Signature", None, True),
        ]
    )
    return CartTool(store)


def test_add_new_item_creates_cart_line(tmp_path):
    tool = _cart_tool(tmp_path)
    cart, message = tool.add([], "chocolate", 2)
    assert cart == [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 2}]
    assert "Chocolate Cake" in message


def test_add_existing_item_increments_quantity(tmp_path):
    tool = _cart_tool(tmp_path)
    cart, _ = tool.add([], "chocolate", 1)
    cart, _ = tool.add(cart, "chocolate", 2)
    assert cart[0]["quantity"] == 3


def test_add_unknown_item_reports_no_match(tmp_path):
    tool = _cart_tool(tmp_path)
    cart, message = tool.add([], "banana bread", 1)
    assert cart == []
    assert message.startswith("NO_MATCH")


def test_remove_item(tmp_path):
    tool = _cart_tool(tmp_path)
    cart, _ = tool.add([], "chocolate", 1)
    cart, message = tool.remove(cart, "chocolate")
    assert cart == []
    assert "Removed" in message


def test_update_quantity_to_zero_removes_item(tmp_path):
    tool = _cart_tool(tmp_path)
    cart, _ = tool.add([], "chocolate", 1)
    cart, _ = tool.update_quantity(cart, "chocolate", 0)
    assert cart == []


def test_clear_empties_cart(tmp_path):
    tool = _cart_tool(tmp_path)
    cart, _ = tool.add([], "chocolate", 1)
    cart, message = tool.clear(cart)
    assert cart == []
    assert message == "Cart cleared."


def test_compute_totals_applies_discount_and_waives_delivery_fee_above_minimum():
    cart = [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 1}]
    totals = compute_totals(cart, _business_config())
    assert totals.subtotal == 500.0
    assert totals.discount == 125.0
    assert totals.qualifies_for_free_delivery is True
    assert totals.delivery_fee == 0.0
    assert totals.total == 375.0


def test_compute_totals_charges_delivery_fee_below_minimum():
    cart = [{"name": "Small Cupcake", "unit_price": 100.0, "quantity": 1}]
    totals = compute_totals(cart, _business_config())
    assert totals.qualifies_for_free_delivery is False
    assert totals.delivery_fee == 75.0
    assert totals.total == 100.0 - 25.0 + 75.0


def test_format_cart_empty_returns_placeholder():
    assert format_cart([], _business_config()) == "EMPTY_CART"
