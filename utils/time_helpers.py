"""Vaqt bilan ishlash yordamchilari. Barcha ko'rsatiladigan vaqtlar Asia/Tashkent."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from config import settings

TZ = settings.tz

WEEKDAYS_UZ = {
    0: "dushanba",
    1: "seshanba",
    2: "chorshanba",
    3: "payshanba",
    4: "juma",
    5: "shanba",
    6: "yakshanba",
}

MONTHS_UZ = {
    1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
    7: "iyul", 8: "avgust", 9: "sentabr", 10: "oktabr", 11: "noyabr", 12: "dekabr",
}


def now_local() -> datetime:
    """Hozirgi vaqt (Asia/Tashkent)."""
    return datetime.now(TZ)


def today_local() -> date:
    return now_local().date()


def to_utc(dt: datetime) -> datetime:
    """Mahalliy (yoki tz-aware) vaqtni UTC ga aylantiradi (bazaga saqlash uchun)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(tz=None).astimezone(tz=None)  # keep tz-aware


def fmt_time(dt: datetime | time | None) -> str:
    """08:47 ko'rinishida."""
    if dt is None:
        return "—"
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        dt = dt.astimezone(TZ)
        return dt.strftime("%H:%M")
    return dt.strftime("%H:%M")


def fmt_date(d: date) -> str:
    """23-iyul, payshanba."""
    return f"{d.day}-{MONTHS_UZ[d.month]}, {WEEKDAYS_UZ[d.weekday()]}"


def fmt_date_short(d: date) -> str:
    """23-iyul."""
    return f"{d.day}-{MONTHS_UZ[d.month]}"


def fmt_duration(minutes: int | None) -> str:
    """545 -> '9 soat 5 daqiqa'."""
    if not minutes or minutes < 0:
        minutes = 0
    h, m = divmod(int(minutes), 60)
    if h and m:
        return f"{h} soat {m} daqiqa"
    if h:
        return f"{h} soat"
    return f"{m} daqiqa"


def fmt_duration_short(minutes: int | None) -> str:
    """545 -> '9s 5d'."""
    if not minutes or minutes < 0:
        minutes = 0
    h, m = divmod(int(minutes), 60)
    return f"{h}s {m}d"


def minutes_between(a: datetime, b: datetime) -> int:
    """b - a farqi daqiqada (musbat)."""
    return max(0, int((b - a).total_seconds() // 60))


def is_workday(d: date, work_days: str) -> bool:
    """work_days: '1,2,3,4,5,6' (dushanba=1). Yakshanba=7."""
    iso = d.isoweekday()  # dushanba=1 ... yakshanba=7
    allowed = {int(x) for x in work_days.split(",") if x.strip()}
    return iso in allowed


def combine_local(d: date, t: time) -> datetime:
    """Sana + vaqtni tz-aware mahalliy datetime ga birlashtiradi."""
    return datetime.combine(d, t).replace(tzinfo=TZ)


def humanize_relative_day(target: date) -> str | None:
    """Ertaga / Indinga yoki None."""
    delta = (target - today_local()).days
    if delta == 1:
        return "Ertaga"
    if delta == 2:
        return "Indinga"
    return None


def month_start(d: date) -> date:
    return d.replace(day=1)
