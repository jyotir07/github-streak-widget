from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Day:
    date: date
    count: int
    level: str


def current_streak(days, today):
    active = {day.date for day in days if day.count > 0}
    # Today without a contribution yet shouldn't break the streak.
    cursor = today if today in active else today - timedelta(days=1)
    streak = 0
    while cursor in active:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def recent_levels(days, today, n=38):
    levels = {day.date: day.level for day in days}
    return [levels.get(today - timedelta(days=offset), "NONE") for offset in range(n - 1, -1, -1)]
