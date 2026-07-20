from app.config import get_settings
from app.store.menu_store import MenuStore
from app.store.models import MenuItem


def _store(tmp_path) -> MenuStore:
    settings = get_settings().model_copy(update={"menu_file_path": tmp_path / "menu.json"})
    return MenuStore(settings)


def _item(name: str, **overrides) -> MenuItem:
    defaults = dict(
        name=name, description=None, price=100.0, category=None, image_url=None,
        is_available=True,
    )
    defaults.update(overrides)
    return MenuItem(**defaults)


def test_load_all_returns_empty_when_file_missing(tmp_path):
    assert _store(tmp_path).load_all() == []


def test_save_and_load_round_trip(tmp_path):
    store = _store(tmp_path)
    items = [
        _item("Cake A", description="desc", price=100.0, category="Chocolate"),
        _item("Cake B", price=200.0, is_available=False),
    ]
    store.save_all(items)

    loaded = store.load_all()
    assert loaded == items


def test_load_available_excludes_unavailable_items(tmp_path):
    store = _store(tmp_path)
    store.save_all(
        [
            _item("Available Cake", is_available=True),
            _item("Sold Out Cake", is_available=False),
        ]
    )
    available = store.load_available()
    assert [item.name for item in available] == ["Available Cake"]


def test_search_matches_name_description_and_category(tmp_path):
    store = _store(tmp_path)
    store.save_all(
        [
            _item("Chocolate Truffle", description="Rich cocoa", category="Chocolate"),
            _item("Vanilla Sponge", description="Light and fluffy", category="Classic"),
        ]
    )
    results = store.search("cocoa")
    assert [item.name for item in results] == ["Chocolate Truffle"]
