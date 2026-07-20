import re
from datetime import datetime, timedelta

_SLOT_COUNT = 6


def generate_slots(now: datetime) -> list[str]:
    """Generate 1-hour delivery slots starting from the next full hour."""
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    slots = []
    for i in range(_SLOT_COUNT):
        slot_start = start + timedelta(hours=i)
        slot_end = slot_start + timedelta(hours=1)
        slots.append(f"{slot_start.strftime('%I%p').lstrip('0')}-{slot_end.strftime('%I%p').lstrip('0')}")
    return slots


_RANGE_MERIDIEM_RE = re.compile(r"(\d{1,2})\s*-\s*(\d{1,2})\s*(am|pm)")


def _extract_hours(text: str) -> list[int]:
    # "3-4pm" implies both ends share the trailing meridiem.
    text = _RANGE_MERIDIEM_RE.sub(r"\1\3-\2\3", text.lower())

    hours = []
    for match in re.finditer(r"(\d{1,2})\s*(am|pm)?", text):
        hour = int(match.group(1))
        if hour > 23:
            continue
        meridiem = match.group(2)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        hours.append(hour % 24)
    return hours


def match_slot(customer_text: str, valid_slots: list[str]) -> str | None:
    """Loosely match free-text customer input (e.g. '3-4pm', '3 to 4')
    against the generated slot list. Returns the canonical slot string,
    or None if it doesn't match any valid slot.
    """
    customer_hours = _extract_hours(customer_text)
    if not customer_hours:
        return None

    for slot in valid_slots:
        slot_hours = _extract_hours(slot)
        if slot_hours and slot_hours[0] == customer_hours[0]:
            return slot
    return None
