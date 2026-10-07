# Public contribution calendar

`update_contributions.py` reads GitHub's unauthenticated contribution calendar and saves only the username, source URL, retrieval time, total, and daily anonymous counts. No access token is used to fetch activity, and no repository names are collected.

GitHub Actions runs the update daily at 12:00 UTC (07:00 in Colombia). It saves the refreshed JSON as `github-actions[bot]`, then explicitly requests and checks a GitHub Pages build. Bot commits do not represent the profile owner's contributions.

The visible date range and last update time come from the JSON; the time is displayed in Colombia's timezone. A failed fetch or invalid response leaves the last good snapshot intact and fails the workflow.

Run locally:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/update_contributions.py
```

Run an extra update from the repository's Actions tab, or:

```sh
gh workflow run update-contributions.yml --repo anedecos/portfolio
```

GitHub may delay scheduled runs. Public-repository schedules can be disabled after 60 days without repository activity; re-enable the workflow in Actions if that occurs. If GitHub changes its calendar HTML, the parser will reject incomplete or inconsistent data until updated.
