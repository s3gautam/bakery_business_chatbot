from datetime import datetime

from app.services.delivery_slots import generate_slots, match_slot


def test_generate_slots_returns_six_hourly_slots():
    slots = generate_slots(datetime(2026, 7, 20, 10, 15))
    assert len(slots) == 6
    assert slots[0] == "11AM-12PM"


def test_match_slot_finds_matching_hour():
    valid_slots = ["2PM-3PM", "3PM-4PM", "4PM-5PM"]
    assert match_slot("3-4pm works for me", valid_slots) == "3PM-4PM"


def test_match_slot_returns_none_when_no_hour_present():
    valid_slots = ["2PM-3PM", "3PM-4PM"]
    assert match_slot("whenever is fine", valid_slots) is None


def test_match_slot_returns_none_for_out_of_range_hour():
    valid_slots = ["2PM-3PM", "3PM-4PM"]
    assert match_slot("9pm please", valid_slots) is None
