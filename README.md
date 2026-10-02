# github-streak-widget

A dark GitHub contribution-streak badge for your profile README. A daily GitHub Action queries the GraphQL API, counts your current streak and writes `dist/streak.svg`.

The streak counts consecutive days with at least one contribution in GitHub's contribution calendar (commits, PRs, reviews, issues, …), so it's a contribution streak, not commit-only. A day with no contribution yet doesn't break the streak until it's over.

## Setup

1. Fork or create this repo as public.
2. Create a [fine-grained personal access token](https://github.com/settings/personal-access-tokens) with read-only access. The contribution calendar is public profile data, so no repository permissions should be needed; if the workflow fails with a permissions error, revisit the token's access.
3. In the repo, go to **Settings → Secrets and variables → Actions** and add a repository secret `GH_TOKEN` with the token.
4. Optional: add a repository **variable** `STREAK_TZ` with an IANA timezone (e.g. `Asia/Kolkata`) to decide when "today" starts. Defaults to UTC.
5. Run **Actions → Update streak widget → Run workflow**. After that it runs daily at 00:17 UTC.

The username is taken from the repo owner, so nothing is hardcoded.

## Embed

```html
<p align="center">
  <img src="https://raw.githubusercontent.com/jyotir07/github-streak-widget/main/dist/streak.svg" alt="GitHub contribution streak" width="820" />
</p>
```

## Development

Python 3.11, standard library only.

```bash
python -m unittest discover -s tests
GITHUB_USER=jyotir07 GH_TOKEN=... python generate.py   # writes dist/streak.svg
```
