from app.agent.tools.menu_tool import format_menu_items
from app.models.menu_item import MenuItem


def test_format_menu_items_returns_placeholder_when_empty():
    assert format_menu_items([]) == "NO_MATCHING_ITEMS"


def test_format_menu_items_includes_name_and_price():
    item = MenuItem(name="Chocolate Truffle Cake", price=499.0, category="Chocolate")
    output = format_menu_items([item])
    assert "Chocolate Truffle Cake" in output
    assert "499" in output
    assert "Chocolate" in output
