import json
import time as time_module
import urllib.error
import urllib.request
from datetime import date, datetime, time, timezone

from streak import Day

API_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""
ATTEMPTS = 3
RETRY_STATUSES = {429, 500, 502, 503, 504}


def fetch_days(login, token, start, end, urlopen=urllib.request.urlopen, sleep=time_module.sleep):
    variables = {
        "login": login,
        "from": datetime.combine(start, time(0, 0), timezone.utc).isoformat(),
        "to": datetime.combine(end, time(23, 59, 59), timezone.utc).isoformat(),
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-streak-widget",
        },
    )
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urlopen(request, timeout=30) as response:
                return parse_days(json.loads(response.read()), login)
        except urllib.error.HTTPError as error:
            if error.code not in RETRY_STATUSES or attempt == ATTEMPTS:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == ATTEMPTS:
                raise
        sleep(2**attempt)


def parse_days(result, login):
    if result.get("errors"):
        raise RuntimeError(f"GitHub API error: {result['errors']}")
    user = result["data"]["user"]
    if user is None:
        raise RuntimeError(f"GitHub user not found: {login}")
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [
        Day(date.fromisoformat(day["date"]), day["contributionCount"], day["contributionLevel"])
        for week in weeks
        for day in week["contributionDays"]
    ]
