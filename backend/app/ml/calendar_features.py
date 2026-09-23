from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import date, timedelta

import pandas as pd


# Це календарні свята / суспільно значущі дати. Під час воєнного стану
# наявність свята не обов'язково означає офіційний неробочий день.
def _orthodox_easter(year: int) -> date:
    """Православний Великдень за юліанським алгоритмом, переведений у григоріанський календар."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    # Різниця 13 днів справедлива для діапазону років, з яким працює цей проєкт.
    return date(year, month, day) + timedelta(days=13)


def ukrainian_calendar_events(year: int) -> dict[date, str]:
    easter = _orthodox_easter(year)
    events: dict[date, str] = {
        date(year, 1, 1): "Новий рік",
        date(year, 3, 8): "Міжнародний жіночий день",
        date(year, 5, 1): "День праці",
        date(year, 6, 28): "День Конституції України",
        date(year, 8, 24): "День Незалежності України",
        date(year, 12, 25): "Різдво Христове",
        date(year, 12, 31): "Переддень Нового року",
        easter: "Великдень",
        easter + timedelta(days=49): "Трійця",
    }

    if year >= 2024:
        events[date(year, 5, 8)] = "День пам'яті та перемоги над нацизмом"
        events[date(year, 7, 15)] = "День Української Державності"
    else:
        events[date(year, 5, 9)] = "День перемоги над нацизмом"
        if year >= 2022:
            events[date(year, 7, 28)] = "День Української Державності"

    if year >= 2023:
        events[date(year, 10, 1)] = "День захисників і захисниць України"
    else:
        events[date(year, 10, 14)] = "День захисників і захисниць України"

    return events


def _events_for_range(min_year: int, max_year: int) -> dict[date, str]:
    events: dict[date, str] = {}
    for year in range(min_year - 1, max_year + 2):
        events.update(ukrainian_calendar_events(year))
    return events


def add_holiday_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        for column in [
            "is_holiday",
            "day_before_holiday",
            "day_after_holiday",
            "days_to_holiday",
            "days_since_holiday",
        ]:
            out[column] = 0
        return out

    dates = out["date"].dt.date
    events = _events_for_range(int(out["date"].dt.year.min()), int(out["date"].dt.year.max()))
    event_dates = sorted(events)
    event_set = set(event_dates)

    def days_to(value: date) -> int:
        index = bisect_left(event_dates, value)
        return (event_dates[index] - value).days if index < len(event_dates) else 366

    def days_since(value: date) -> int:
        index = bisect_right(event_dates, value) - 1
        return (value - event_dates[index]).days if index >= 0 else 366

    out["is_holiday"] = dates.map(lambda value: int(value in event_set))
    out["day_before_holiday"] = dates.map(lambda value: int((value + timedelta(days=1)) in event_set))
    out["day_after_holiday"] = dates.map(lambda value: int((value - timedelta(days=1)) in event_set))
    out["days_to_holiday"] = dates.map(days_to).clip(upper=60).astype(int)
    out["days_since_holiday"] = dates.map(days_since).clip(upper=60).astype(int)
    return out


def holiday_name(value: pd.Timestamp | date) -> str | None:
    current = value.date() if isinstance(value, pd.Timestamp) else value
    return ukrainian_calendar_events(current.year).get(current)
