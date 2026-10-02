import unittest
from datetime import date, timedelta

from streak import Day, current_streak, recent_levels

TODAY = date(2026, 10, 2)


def run(end, length, count=1, level="FIRST_QUARTILE"):
    return [Day(end - timedelta(days=i), count, level) for i in range(length)]


class CurrentStreakTest(unittest.TestCase):
    def test_streak_includes_today_when_active(self):
        self.assertEqual(current_streak(run(TODAY, 5), TODAY), 5)

    def test_streak_counts_from_yesterday_when_today_empty(self):
        days = run(TODAY - timedelta(days=1), 3) + [Day(TODAY, 0, "NONE")]
        self.assertEqual(current_streak(days, TODAY), 3)

    def test_streak_zero_when_yesterday_and_today_empty(self):
        days = run(TODAY - timedelta(days=2), 4)
        self.assertEqual(current_streak(days, TODAY), 0)

    def test_gap_breaks_streak(self):
        days = run(TODAY, 2) + run(TODAY - timedelta(days=3), 10)
        self.assertEqual(current_streak(days, TODAY), 2)

    def test_zero_count_days_are_not_active(self):
        days = run(TODAY, 3, count=0, level="NONE")
        self.assertEqual(current_streak(days, TODAY), 0)


class RecentLevelsTest(unittest.TestCase):
    def test_returns_38_levels_oldest_first(self):
        days = [Day(TODAY, 4, "FOURTH_QUARTILE"), Day(TODAY - timedelta(days=37), 1, "FIRST_QUARTILE")]
        levels = recent_levels(days, TODAY)
        self.assertEqual(len(levels), 38)
        self.assertEqual(levels[0], "FIRST_QUARTILE")
        self.assertEqual(levels[-1], "FOURTH_QUARTILE")

    def test_missing_days_are_none(self):
        self.assertEqual(recent_levels([], TODAY), ["NONE"] * 38)


if __name__ == "__main__":
    unittest.main()
