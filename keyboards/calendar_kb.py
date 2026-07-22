"""Inline kalendar (aiogram_calendar) o'rovi. O'tgan sana tanlab bo'lmaydi, maks +30 kun."""
from __future__ import annotations

from datetime import timedelta

from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from utils.time_helpers import today_local


async def get_calendar():
    """Bugundan +30 kungacha tanlash mumkin bo'lgan kalendar."""
    cal = SimpleCalendar(show_alerts=True)
    start = today_local()
    end = start + timedelta(days=30)
    cal.set_dates_range(
        _to_dt(start),
        _to_dt(end),
    )
    return cal


def _to_dt(d):
    from datetime import datetime

    return datetime(d.year, d.month, d.day)


__all__ = ["get_calendar", "SimpleCalendar", "SimpleCalendarCallback"]
