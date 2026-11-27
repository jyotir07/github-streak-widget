import io
import json
import unittest
import urllib.error
from datetime import date

from github_api import fetch_days, parse_days
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


def http_error(code):
    return urllib.error.HTTPError("https://api.github.com/graphql", code, "error", {}, None)


def fake_urlopen(*outcomes):
    calls = []

    def urlopen(request, timeout):
        outcome = outcomes[len(calls)]
        calls.append(request)
        if isinstance(outcome, Exception):
            raise outcome
        return io.BytesIO(json.dumps(outcome).encode())

    return urlopen, calls


OK = response([{"contributionDays": [{"date": "2026-10-02", "contributionCount": 1, "contributionLevel": "FIRST_QUARTILE"}]}])
DAY = date(2026, 10, 2)


class FetchDaysRetryTest(unittest.TestCase):
    def setUp(self):
        self.sleeps = []

    def fetch(self, urlopen):
        return fetch_days("u", "t", DAY, DAY, urlopen=urlopen, sleep=self.sleeps.append)

    def test_retries_server_errors_then_succeeds(self):
        urlopen, calls = fake_urlopen(http_error(502), urllib.error.URLError("reset"), OK)
        self.assertEqual(self.fetch(urlopen), [Day(DAY, 1, "FIRST_QUARTILE")])
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.sleeps, [2, 4])

    def test_gives_up_after_last_attempt(self):
        urlopen, calls = fake_urlopen(TimeoutError(), TimeoutError(), TimeoutError())
        with self.assertRaises(TimeoutError):
            self.fetch(urlopen)
        self.assertEqual(len(calls), 3)

    def test_does_not_retry_client_errors(self):
        urlopen, calls = fake_urlopen(http_error(401))
        with self.assertRaises(urllib.error.HTTPError):
            self.fetch(urlopen)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.sleeps, [])


if __name__ == "__main__":
    unittest.main()
