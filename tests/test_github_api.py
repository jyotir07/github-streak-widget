import unittest
from datetime import date

from github_api import parse_days
from streak import Day


def response(weeks):
    return {"data": {"user": {"contributionsCollection": {"contributionCalendar": {"weeks": weeks}}}}}


class ParseDaysTest(unittest.TestCase):
    def test_flattens_weeks_into_days(self):
        result = response([
            {"contributionDays": [{"date": "2026-09-27", "contributionCount": 0, "contributionLevel": "NONE"}]},
            {"contributionDays": [{"date": "2026-10-02", "contributionCount": 7, "contributionLevel": "THIRD_QUARTILE"}]},
        ])
        self.assertEqual(parse_days(result, "jyotir07"), [
            Day(date(2026, 9, 27), 0, "NONE"),
            Day(date(2026, 10, 2), 7, "THIRD_QUARTILE"),
        ])

    def test_parse_raises_on_errors(self):
        result = {"data": {"user": None}, "errors": [{"message": "Could not resolve to a User"}]}
        with self.assertRaisesRegex(RuntimeError, "Could not resolve"):
            parse_days(result, "nobody")

    def test_parse_raises_on_missing_user(self):
        with self.assertRaisesRegex(RuntimeError, "user not found: nobody"):
            parse_days({"data": {"user": None}}, "nobody")


if __name__ == "__main__":
    unittest.main()
