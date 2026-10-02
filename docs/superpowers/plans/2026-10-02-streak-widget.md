# GitHub Streak Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily GitHub Action that generates `dist/streak.svg`, a badge matching `docs/superpowers/plans/github streak.png` (twin glass panels with a flame and the streak count, then a 2×19 activity grid), for embedding in the profile README.

**Architecture:** Four small stdlib-only Python modules. `streak.py` holds the pure date logic, `github_api.py` fetches and parses the GraphQL contribution calendar, `render.py` turns `(streak, levels)` into SVG text, and `generate.py` wires them together. A scheduled workflow runs the tests, generates the SVG and commits it when it changes.

**Tech Stack:** Python 3.11 (stdlib only: `urllib`, `json`, `zoneinfo`, `xml.etree` for tests, `unittest`), GitHub GraphQL API, GitHub Actions.

**Spec:** `docs/github-streak-widget-guide.md` (pipeline) + `docs/superpowers/plans/github streak.png` (visual target). This plan deliberately departs from the guide in the places listed under Global Constraints.

## Global Constraints

- No third-party dependencies. Tests use `unittest`, not pytest, so `requirements.txt` stays empty and nothing needs installing in CI.
- The token is only ever read from the `GH_TOKEN` env var. It never goes in code, the SVG, logs or the README.
- The username comes from the `GITHUB_USER` env var (the workflow sets it to `github.repository_owner`), so it isn't hardcoded.
- Visual content matches the reference image: no "LAST 28 DAYS", "Longest streak" or "LIVE DATA" text. Longest streak is dropped entirely.
- Grid is 38 days: top row = the older 19 days, bottom row = the most recent 19, left→right. Today is bottom-right.
- Tile shading uses GitHub's own `contributionLevel` quartiles (`NONE`, `FIRST_QUARTILE` … `FOURTH_QUARTILE`), not hand-picked count thresholds, so it matches the profile graph's shading.
- SVG canvas is `1660×260`, transparent outside the badge. Embed at `width="820"`.
- Commits: the executor never runs `git commit`. At each checkpoint it shows `git status --short` and hands over a conventional-commit message with no trailers.
- Run tests with `python -m unittest discover -s tests` from the repo root.

## Review Focus

1. **Streak longer than one API window (>364 days).** `contributionsCollection` caps at one year per query, so the count must keep going across windows instead of stopping at ~365. Pinned by `test_fetch_streak_days_extends_past_one_window` (Task 4).
2. **No contribution yet today.** The streak must count up to yesterday, not drop to 0 in the morning. Pinned by `test_streak_counts_from_yesterday_when_today_empty` (Task 1).
3. **3–4 digit streaks.** The number must fit inside the number panel. Pinned by `test_font_shrinks_for_long_numbers` (Task 3).
4. **Wrong username / bad token.** The job must fail loudly and keep serving the previous SVG, not write a "0" badge. Pinned by `test_parse_raises_on_errors` and `test_parse_raises_on_missing_user` (Task 2); the workflow only commits after `generate.py` succeeds.
5. **Timezone day boundary.** "Today" uses `STREAK_TZ` (default UTC). I don't know for sure which timezone GitHub's API uses to bucket calendar days, so Task 5 has a manual check against the profile graph. Not unit-testable.

---

### Task 0: Make the widget folder its own git repo

`C:\Users\jyoti` is currently a git repo, and this folder is tracked inside it. The widget has to become a standalone public repo (`github-streak-widget`).

- [ ] **Step 1:** Confirm with the user, then run `git init -b main` in `C:\Users\jyoti\Desktop\Coding\git-widget`.
- [ ] **Step 2:** Create `.gitignore`:

```gitignore
__pycache__/
*.pyc
preview/
```

- [x] **Step 3:** Keep `github streak.png` (design target, now in `docs/superpowers/plans/`) and the guide (now in `docs/`) in the repo — confirmed by user.

---

### Task 1: Streak logic

**Files:**
- Create: `streak.py`
- Test: `tests/test_streak.py`

**Interfaces:**
- Produces: `Day(date: date, count: int, level: str)` (frozen dataclass); `current_streak(days: list[Day], today: date) -> int`; `recent_levels(days: list[Day], today: date, n: int = 38) -> list[str]` (oldest first).

- [ ] **Step 1: Write the failing tests** in `tests/test_streak.py`:

```python
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
```

- [ ] **Step 2: Run** `python -m unittest discover -s tests`. Expected: `ModuleNotFoundError: No module named 'streak'`.

- [ ] **Step 3: Implement** `streak.py`:

```python
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
```

- [ ] **Step 4: Run** `python -m unittest discover -s tests`. Expected: 7 tests OK.

---

### Task 2: GitHub API client

**Files:**
- Create: `github_api.py`
- Test: `tests/test_github_api.py`

**Interfaces:**
- Consumes: `Day` from `streak.py`.
- Produces: `fetch_days(login: str, token: str, start: date, end: date) -> list[Day]` (span must be ≤ 1 year); `parse_days(result: dict, login: str) -> list[Day]`.

- [ ] **Step 1: Write the failing tests** in `tests/test_github_api.py`:

```python
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
```

- [ ] **Step 2: Run** the tests. Expected: `ModuleNotFoundError: No module named 'github_api'`.

- [ ] **Step 3: Implement** `github_api.py`:

```python
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
```

No retries: the job runs daily and can be re-run by hand, and a failed run leaves the last good SVG in place.

- [ ] **Step 4: Run** the tests. Expected: 10 tests OK.

- [ ] **Step 5: Checkpoint.** Show `git status --short` and hand over:

```
feat: add streak calculation and GitHub contribution client
```

STOP until the user has committed.

---

### Task 3: SVG renderer

**Files:**
- Create: `render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Produces: `render_svg(streak: int, levels: list[str]) -> str`. `levels` must have exactly 38 entries, each a key of `LEVEL_FILLS`. Raises `ValueError` on the wrong length and `KeyError` on an unknown level, so a GitHub enum change fails the job instead of silently rendering wrong colours.

Geometry was measured from the 1983×793 reference image (badge at roughly x 182–1805, y 280–502) and shifted by (−164, −261) into a 1660×260 canvas:

| Element | Box |
|---|---|
| Outer badge | x 18, y 19, 1624×222, rx 56 |
| Flame panel | x 31–264, y 34–226, r 40 |
| Number panel | x 298–534, y 34–226, r 40, joined to the flame panel by a pinched neck |
| Flame inner tile | x 63, y 51, 170×158, rx 36 |
| Flame | 100×130 centred at (148, 130) |
| Number | centred x 416, baseline 176, font 128 (shrinks for 3+ digits) |
| Tiles | 42×42, rx 9, pitch 55, first x 571, rows y 82 / 136 |

- [ ] **Step 1: Write the failing tests** in `tests/test_render.py`:

```python
import unittest
import xml.etree.ElementTree as ET

from render import render_svg

NS = {"svg": "http://www.w3.org/2000/svg"}
LEVELS = ["NONE"] * 37 + ["FOURTH_QUARTILE"]


def parse(svg):
    return ET.fromstring(svg)


class RenderSvgTest(unittest.TestCase):
    def test_is_valid_svg_with_expected_canvas(self):
        root = parse(render_svg(24, LEVELS))
        self.assertEqual((root.get("width"), root.get("height")), ("1660", "260"))

    def test_shows_streak_number_and_label(self):
        root = parse(render_svg(24, LEVELS))
        number = root.find(".//svg:text[@id='streak']", NS)
        self.assertEqual(number.text, "24")
        self.assertIn("24 day", root.get("aria-label"))

    def test_draws_38_tiles_in_two_rows_oldest_top_left(self):
        tiles = parse(render_svg(24, LEVELS)).findall(".//svg:rect[@class='tile']", NS)
        self.assertEqual(len(tiles), 38)
        self.assertEqual((tiles[0].get("x"), tiles[0].get("y")), ("571", "82"))
        self.assertEqual((tiles[18].get("x"), tiles[18].get("y")), ("1561", "82"))
        self.assertEqual((tiles[37].get("x"), tiles[37].get("y")), ("1561", "136"))

    def test_top_level_tile_glows(self):
        tiles = parse(render_svg(24, LEVELS)).findall(".//svg:rect[@class='tile']", NS)
        self.assertEqual(tiles[37].get("filter"), "url(#glow)")
        self.assertIsNone(tiles[0].get("filter"))

    def test_font_shrinks_for_long_numbers(self):
        def size(streak):
            root = parse(render_svg(streak, LEVELS))
            return int(root.find(".//svg:text[@id='streak']", NS).get("font-size"))

        self.assertEqual(size(7), 128)
        self.assertEqual(size(24), 128)
        self.assertEqual(size(365), 100)
        self.assertEqual(size(1200), 80)

    def test_rejects_wrong_level_count(self):
        with self.assertRaises(ValueError):
            render_svg(1, ["NONE"] * 28)

    def test_rejects_unknown_level(self):
        with self.assertRaises(KeyError):
            render_svg(1, ["NONE"] * 37 + ["BOGUS"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** the tests. Expected: `ModuleNotFoundError: No module named 'render'`.

- [ ] **Step 3: Implement** `render.py`:

```python
WIDTH, HEIGHT = 1660, 260
COLUMNS = 19
TILE_SIZE, TILE_PITCH, TILE_X = 42, 55, 571
TILE_ROWS_Y = (82, 136)

LEVEL_FILLS = {
    "NONE": "#16232a",
    "FIRST_QUARTILE": "#1d3d35",
    "SECOND_QUARTILE": "#27704b",
    "THIRD_QUARTILE": "#41b06c",
    "FOURTH_QUARTILE": "#b9f7cf",
}

# Two rounded panels joined by a pinched neck, drawn as one path so the outline has no seams.
TWIN_PANEL = (
    "M71 34 H220 C248 34 258 52 266 70 C272 84 290 84 296 70 C304 52 314 34 342 34 "
    "H494 A40 40 0 0 1 534 74 V186 A40 40 0 0 1 494 226 "
    "H342 C314 226 304 208 296 190 C290 176 272 176 266 190 C258 208 248 226 220 226 "
    "H71 A40 40 0 0 1 31 186 V74 A40 40 0 0 1 71 34 Z"
)
FLAME = (
    "M50 0 C58 18 78 30 80 58 C82 82 66 100 50 100 C34 100 18 86 20 62 "
    "C21 48 28 40 34 34 C34 46 38 52 44 54 C40 36 44 16 50 0 Z"
)
FLAME_CORE = "M50 62 C58 72 60 82 56 90 C54 95 46 95 44 90 C40 82 42 72 50 62 Z"


def font_size(streak):
    digits = len(str(streak))
    if digits <= 2:
        return 128
    if digits == 3:
        return 100
    return 80


def render_tiles(levels):
    tiles = []
    for i, level in enumerate(levels):
        row, col = divmod(i, COLUMNS)
        glow = ' filter="url(#glow)"' if level == "FOURTH_QUARTILE" else ""
        tiles.append(
            f'<rect class="tile" x="{TILE_X + col * TILE_PITCH}" y="{TILE_ROWS_Y[row]}" '
            f'width="{TILE_SIZE}" height="{TILE_SIZE}" rx="9" fill="{LEVEL_FILLS[level]}"{glow}/>'
        )
    return "\n  ".join(tiles)


def render_svg(streak, levels):
    if len(levels) != len(TILE_ROWS_Y) * COLUMNS:
        raise ValueError(f"expected {len(TILE_ROWS_Y) * COLUMNS} levels, got {len(levels)}")
    tiles = render_tiles(levels)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{streak} day GitHub contribution streak">
  <title>{streak} day GitHub contribution streak</title>
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="haze" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
    <linearGradient id="badgeStroke" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#4fd1a5" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#2a4a46" stop-opacity="0.6"/>
    </linearGradient>
    <linearGradient id="panelFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#14231f"/>
      <stop offset="100%" stop-color="#0c1715"/>
    </linearGradient>
    <linearGradient id="flameFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#86f7b4"/>
      <stop offset="100%" stop-color="#2dd4bf"/>
    </linearGradient>
    <linearGradient id="numberFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#effff5"/>
      <stop offset="100%" stop-color="#a3f0c8"/>
    </linearGradient>
  </defs>
  <rect x="18" y="19" width="1624" height="222" rx="56" fill="#0a1214" fill-opacity="0.92" stroke="url(#badgeStroke)" stroke-width="2"/>
  <path d="{TWIN_PANEL}" fill="none" stroke="#4fd1a5" stroke-opacity="0.45" stroke-width="6" filter="url(#haze)"/>
  <path d="{TWIN_PANEL}" fill="url(#panelFill)" stroke="#5fe0b4" stroke-opacity="0.6" stroke-width="2"/>
  <rect x="63" y="51" width="170" height="158" rx="36" fill="#0f1c1b" stroke="#2c4c45" stroke-width="1.5"/>
  <g transform="translate(98 65) scale(1 1.3)" filter="url(#glow)">
    <path d="{FLAME}" fill="url(#flameFill)"/>
    <path d="{FLAME_CORE}" fill="#0f1c1b"/>
  </g>
  <text id="streak" x="416" y="176" text-anchor="middle" font-family="'Segoe UI', Inter, Arial, sans-serif" font-size="{font_size(streak)}" font-weight="700" fill="url(#numberFill)" filter="url(#glow)">{streak}</text>
  {tiles}
</svg>
'''
```

- [ ] **Step 4: Run** the tests. Expected: 17 tests OK.

- [ ] **Step 5: Visual check against the reference.** Write a preview with fake data and screenshot it with headless Edge:

```bash
mkdir -p preview
python -c "
from render import render_svg
levels = ['NONE','FIRST_QUARTILE','SECOND_QUARTILE','THIRD_QUARTILE','FOURTH_QUARTILE'] * 7 + ['NONE'] * 3
open('preview/streak.html', 'w').write('<body style=\"margin:0;background:#000\">' + render_svg(24, levels) + '</body>')
"
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless --disable-gpu --hide-scrollbars --window-size=1660,260 --screenshot="$(pwd -W)/preview/streak.png" "file:///$(pwd -W)/preview/streak.html"
```

Read `preview/streak.png` and `docs/superpowers/plans/github streak.png` side by side. Adjust the colour hexes, neck curve, flame path and glow strength until the proportions and mood match. Change only constants in `render.py`; if any coordinate changes, update the tile-position test to match. Show the user the screenshot before moving on.

- [ ] **Step 6: Checkpoint.** Hand over:

```
feat: render streak badge SVG matching reference design
```

STOP until the user has committed.

---

### Task 4: Entry point with multi-year streaks

**Files:**
- Create: `generate.py`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `fetch_days`, `current_streak`, `recent_levels`, `render_svg`.
- Produces: `fetch_streak_days(login, token, today, fetch=fetch_days) -> list[Day]`; `main()`. Reads env `GITHUB_USER`, `GH_TOKEN`, and optional `STREAK_TZ` (IANA name, e.g. `Asia/Kolkata`). Writes `dist/streak.svg`.

- [ ] **Step 1: Write the failing tests** in `tests/test_generate.py`:

```python
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
```

- [ ] **Step 2: Run** the tests. Expected: `ModuleNotFoundError: No module named 'generate'`.

- [ ] **Step 3: Implement** `generate.py`:

```python
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
```

The loop always terminates: days before the account existed have a count of 0, so the streak ends inside some window. `timezone.utc` is used when `STREAK_TZ` is unset because `ZoneInfo("UTC")` fails on Windows without the `tzdata` package.

- [ ] **Step 4: Run** the tests. Expected: 20 tests OK.

---

### Task 5: Workflow, embed snippet, live verification

**Files:**
- Create: `.github/workflows/update-streak.yml`
- Create: `README.md`

- [ ] **Step 1: Create** `.github/workflows/update-streak.yml`:

```yaml
name: Update streak widget

on:
  workflow_dispatch:
  schedule:
    - cron: "17 0 * * *"

permissions:
  contents: write

concurrency:
  group: update-streak
  cancel-in-progress: false

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Test
        run: python -m unittest discover -s tests

      - name: Generate SVG
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          GITHUB_USER: ${{ github.repository_owner }}
          STREAK_TZ: ${{ vars.STREAK_TZ }}
        run: python generate.py

      - name: Commit updated widget
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add dist/streak.svg
          git diff --staged --quiet || git commit -m "chore: refresh streak widget"
          git push
```

- [ ] **Step 2: Create** `README.md`. It covers the setup (fine-grained PAT → `GH_TOKEN` secret; optional `STREAK_TZ` repository variable), how to run tests locally, and the embed snippet:

```html
<p align="center">
  <img src="https://raw.githubusercontent.com/jyotir07/github-streak-widget/main/dist/streak.svg" alt="GitHub contribution streak" width="820" />
</p>
```

- [ ] **Step 3: Run** `python -m unittest discover -s tests` one final time. Expected: 20 tests OK.

- [ ] **Step 4: Checkpoint.** Hand over:

```
feat: add generator entry point and daily update workflow
```

STOP until the user has committed.

- [ ] **Step 5: Live verification (done by the user, guided by the executor).**
  1. Create the public repo `jyotir07/github-streak-widget` and push.
  2. Add the `GH_TOKEN` secret, and optionally set the `STREAK_TZ` variable (e.g. `Asia/Kolkata`).
  3. Actions → **Update streak widget** → Run workflow. Confirm a `chore: refresh streak widget` commit appears.
  4. **Timezone check:** compare the last ~5 tiles and the streak number against the profile contribution graph. If they're off by one day, the API buckets days differently from `STREAK_TZ`. Record the result and adjust.
  5. Open the raw URL, then add the embed snippet to the profile README (`jyotir07/jyotir07`).
