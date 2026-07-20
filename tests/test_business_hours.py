from datetime import datetime

from app.config import get_settings
from app.services.business_hours import BusinessHoursService


def test_open_late_at_night():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 23, 0)) is True


def test_open_in_the_afternoon():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 15, 0)) is True


def test_open_right_before_closed_window():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 4, 59)) is True


def test_closed_during_closed_window():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 7, 0)) is False


def test_closed_at_window_start_boundary():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 5, 0)) is False


def test_open_at_window_end_boundary():
    service = BusinessHoursService(get_settings())
    assert service.is_open(datetime(2026, 7, 20, 9, 0)) is True
