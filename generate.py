import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from github_api import fetch_days
from render import render_svg
from streak import current_streak, recent_levels

OUTPUT = Path("dist/streak.svg")


def fetch_streak_days(login, token, today, fetch=fetch_days):
    days = []
    end = today
    while True:
        start = end - timedelta(days=364)
        days = fetch(login, token, start, end) + days
        # Stop once the streak ends inside what we've fetched; otherwise it may continue further back.
        if current_streak(days, today) < (today - start).days:
            return days
        end = start - timedelta(days=1)


def main():
    login = os.environ["GITHUB_USER"]
    token = os.environ["GH_TOKEN"]
    tz_name = os.environ.get("STREAK_TZ")
    today = datetime.now(ZoneInfo(tz_name) if tz_name else timezone.utc).date()

    days = fetch_streak_days(login, token, today)
    streak = current_streak(days, today)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(render_svg(streak, recent_levels(days, today)), encoding="utf-8")
    print(f"{login}: {streak}-day streak")


if __name__ == "__main__":
    main()
