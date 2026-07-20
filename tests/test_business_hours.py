from datetime import datetime

from app.config import get_settings
from app.services.business_hours import BusinessHoursService


def test_open_during_early_morning_window():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 2, 0)) is True


def test_open_during_late_morning_window():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 10, 0)) is True


def test_closed_outside_windows():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 15, 0)) is False


def test_closed_at_window_boundary_end():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 5, 0)) is False
