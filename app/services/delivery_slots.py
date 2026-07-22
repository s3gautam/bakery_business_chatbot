import re
from datetime import datetime, timedelta

_SLOT_COUNT = 6
# Slots starting in this hour range (inclusive start, exclusive end) are
# never proactively offered, even though the business is technically open
# through the night — only shown if the customer explicitly asks for one.
_LATE_NIGHT_HOURS = range(0, 5)


def _is_closed(hour: int, closed_hours: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= hour < end for start, end in closed_hours)


def generate_slots(
    now: datetime,
    prep_minutes: int = 120,
    closed_hours: tuple[tuple[int, int], ...] = ((5, 9),),
    include_late_night: bool = False,
    count: int = _SLOT_COUNT,
) -> list[str]:
    """Generate 1-hour delivery slots, earliest starting after `prep_minutes`
    of prep time has elapsed from `now`, skipping any slot that starts
    during closed business hours. By default also skips late-night slots
    (12AM-5AM) — pass include_late_night=True to allow matching an
    explicit customer request for one.
    """
    earliest = now + timedelta(minutes=prep_minutes)
    start = earliest.replace(minute=0, second=0, microsecond=0)
    if earliest.minute or earliest.second or earliest.microsecond:
        start += timedelta(hours=1)

    slots = []
    candidate = start
    # Bounded search so a pathological all-closed config can't loop forever.
    for _ in range(24 * 3):
        if len(slots) >= count:
            break
        hour = candidate.hour
        if not _is_closed(hour, closed_hours) and (include_late_night or hour not in _LATE_NIGHT_HOURS):
            slot_end = candidate + timedelta(hours=1)
            slots.append(
                f"{candidate.strftime('%I%p').lstrip('0')}-{slot_end.strftime('%I%p').lstrip('0')}"
            )
        candidate += timedelta(hours=1)
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
