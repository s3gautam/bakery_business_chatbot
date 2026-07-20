from app.agent.tools.menu_tool import format_menu_items
from app.store.models import MenuItem


def test_format_menu_items_returns_placeholder_when_empty():
    assert format_menu_items([]) == "NO_MATCHING_ITEMS"


def test_format_menu_items_includes_name_and_price():
    item = MenuItem(
        name="Chocolate Truffle Cake",
        description=None,
        price=499.0,
        category="Chocolate",
        image_url=None,
    )
    output = format_menu_items([item])
    assert "Chocolate Truffle Cake" in output
    assert "499" in output
    assert "Chocolate" in output
