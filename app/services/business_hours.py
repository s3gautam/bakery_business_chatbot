from datetime import datetime, time

from app.config import Settings

OFFLINE_MESSAGE = (
    "We are currently offline. You may still place an order and we'll "
    "process it during business hours."
)


class BusinessHoursService:
    def __init__(self, settings: Settings) -> None:
        self._windows: tuple[tuple[time, time], ...] = tuple(
            (time(hour=start), time(hour=end)) for start, end in settings.business_hours
        )

    def is_open(self, at: datetime) -> bool:
        current = at.time()
        return any(start <= current < end for start, end in self._windows)
