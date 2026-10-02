import json
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


def fetch_days(login, token, start, end):
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
    with urllib.request.urlopen(request, timeout=30) as response:
        return parse_days(json.loads(response.read()), login)


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
