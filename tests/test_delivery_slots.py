from datetime import datetime

from app.services.delivery_slots import generate_slots, match_slot


def test_generate_slots_returns_six_hourly_slots_after_prep_time():
    # 10:15 + 120min prep = 12:15, rounds up to the next full hour (1PM).
    slots = generate_slots(datetime(2026, 7, 20, 10, 15), prep_minutes=120)
    assert len(slots) == 6
    assert slots[0] == "1PM-2PM"


def test_generate_slots_uses_configured_prep_time():
    slots = generate_slots(datetime(2026, 7, 20, 10, 0), prep_minutes=30)
    assert slots[0] == "11AM-12PM"


def test_generate_slots_skips_closed_business_hours():
    # Prep window lands the first candidate inside 5AM-9AM (closed) —
    # those hours must never be offered.
    slots = generate_slots(
        datetime(2026, 7, 20, 2, 0), prep_minutes=120, closed_hours=((5, 9),)
    )
    assert all(not slot.startswith(("5AM", "6AM", "7AM", "8AM")) for slot in slots)
    assert slots[0] == "9AM-10AM"


def test_generate_slots_excludes_late_night_by_default():
    slots = generate_slots(
        datetime(2026, 7, 20, 22, 0), prep_minutes=120, closed_hours=((5, 9),)
    )
    assert all(not slot.startswith(("12AM", "1AM", "2AM", "3AM", "4AM")) for slot in slots)
    # First non-late-night, non-closed slot after 12AM-4AM is 9AM.
    assert slots[0] == "9AM-10AM"


def test_generate_slots_includes_late_night_when_explicitly_allowed():
    slots = generate_slots(
        datetime(2026, 7, 20, 22, 0),
        prep_minutes=120,
        closed_hours=((5, 9),),
        include_late_night=True,
        count=24,
    )
    assert "1AM-2AM" in slots


def test_match_slot_finds_matching_hour():
    valid_slots = ["2PM-3PM", "3PM-4PM", "4PM-5PM"]
    assert match_slot("3-4pm works for me", valid_slots) == "3PM-4PM"


def test_match_slot_returns_none_when_no_hour_present():
    valid_slots = ["2PM-3PM", "3PM-4PM"]
    assert match_slot("whenever is fine", valid_slots) is None


def test_match_slot_returns_none_for_out_of_range_hour():
    valid_slots = ["2PM-3PM", "3PM-4PM"]
    assert match_slot("9pm please", valid_slots) is None
