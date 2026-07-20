from app.config import get_settings
from app.store.config_store import ConfigStore


def _store(tmp_path) -> ConfigStore:
    settings = get_settings().model_copy(
        update={"business_config_file_path": tmp_path / "business_config.json"}
    )
    return ConfigStore(settings)


def test_load_creates_defaults_when_file_missing(tmp_path):
    store = _store(tmp_path)
    config = store.load()
    assert config.min_cart_for_free_delivery == 300.0
    assert (tmp_path / "business_config.json").exists()


def test_update_persists_only_provided_fields(tmp_path):
    store = _store(tmp_path)
    store.load()

    updated = store.update(discount_percent=30.0)
    assert updated.discount_percent == 30.0
    assert updated.min_cart_for_free_delivery == 300.0

    reloaded = store.load()
    assert reloaded.discount_percent == 30.0
