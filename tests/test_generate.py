import unittest
from datetime import date, timedelta, timezone

from generate import fetch_streak_days, load_config
from streak import Day, current_streak

TODAY = date(2026, 10, 2)


def fake_fetch(active_since):
    calls = []

    def fetch(login, token, start, end):
        calls.append((start, end))
        days = []
        d = start
        while d <= end:
            days.append(Day(d, 1 if d >= active_since else 0, "FIRST_QUARTILE" if d >= active_since else "NONE"))
            d += timedelta(days=1)
        return days

    return fetch, calls


class FetchStreakDaysTest(unittest.TestCase):
    def test_single_window_when_streak_is_short(self):
        fetch, calls = fake_fetch(TODAY - timedelta(days=9))
        days = fetch_streak_days("u", "t", TODAY, fetch=fetch)
        self.assertEqual(len(calls), 1)
        self.assertEqual(current_streak(days, TODAY), 10)

    def test_fetch_streak_days_extends_past_one_window(self):
        fetch, calls = fake_fetch(TODAY - timedelta(days=399))
        days = fetch_streak_days("u", "t", TODAY, fetch=fetch)
        self.assertEqual(len(calls), 2)
        self.assertEqual(current_streak(days, TODAY), 400)

    def test_windows_never_exceed_one_year(self):
        fetch, calls = fake_fetch(TODAY - timedelta(days=800))
        fetch_streak_days("u", "t", TODAY, fetch=fetch)
        for start, end in calls:
            self.assertLessEqual((end - start).days, 364)


class LoadConfigTest(unittest.TestCase):
    def test_defaults_to_utc_when_tz_unset_or_empty(self):
        for env in ({"GITHUB_USER": "u", "GH_TOKEN": "t"}, {"GITHUB_USER": "u", "GH_TOKEN": "t", "STREAK_TZ": ""}):
            self.assertEqual(load_config(env), ("u", "t", timezone.utc))

    def test_uses_named_timezone(self):
        _, _, tz = load_config({"GITHUB_USER": "u", "GH_TOKEN": "t", "STREAK_TZ": "Asia/Kolkata"})
        self.assertEqual(str(tz), "Asia/Kolkata")

    def test_reports_all_missing_variables(self):
        with self.assertRaisesRegex(SystemExit, "GITHUB_USER, GH_TOKEN"):
            load_config({"GH_TOKEN": ""})

    def test_rejects_unknown_timezone(self):
        with self.assertRaisesRegex(SystemExit, "Unknown STREAK_TZ 'Mars/Base'"):
            load_config({"GITHUB_USER": "u", "GH_TOKEN": "t", "STREAK_TZ": "Mars/Base"})


if __name__ == "__main__":
    unittest.main()
