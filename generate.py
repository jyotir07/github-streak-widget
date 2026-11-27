import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def load_config(env):
    missing = [name for name in ("GITHUB_USER", "GH_TOKEN") if not env.get(name)]
    if missing:
        raise SystemExit(f"Missing required environment variable(s): {', '.join(missing)}")
    # The workflow passes an unset repo variable as an empty string, so treat it as UTC.
    tz_name = env.get("STREAK_TZ")
    try:
        tz = ZoneInfo(tz_name) if tz_name else timezone.utc
    except (ZoneInfoNotFoundError, ValueError):
        raise SystemExit(f"Unknown STREAK_TZ {tz_name!r}; use an IANA name like 'Asia/Kolkata'")
    return env["GITHUB_USER"], env["GH_TOKEN"], tz


def main():
    login, token, tz = load_config(os.environ)
    today = datetime.now(tz).date()

    days = fetch_streak_days(login, token, today)
    streak = current_streak(days, today)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(render_svg(streak, recent_levels(days, today)), encoding="utf-8")
    print(f"{login}: {streak}-day streak")


if __name__ == "__main__":
    main()
