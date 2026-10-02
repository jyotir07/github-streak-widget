import unittest
from datetime import date, timedelta

from generate import fetch_streak_days
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


if __name__ == "__main__":
    unittest.main()
