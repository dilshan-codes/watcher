# watcher

# A GitHub Repo Watcher

A small tool that tracks activity on repositories you own — traffic stats
(views, clones, referrers) and identity-level events (new stargazers,
watchers, forkers) — and emails you a summary when something changes.
Runs automatically on a schedule using GitHub Actions.

> **This is the demo/reference copy.** It's not connected to any live repo
> or credentials — it just shows the code and how the project is structured.
> If you want to actually run it against your own repos, see "Running your
> own copy" below — you'll want to do that in a **private** repo, not this one.

## What it does

- Pulls traffic data (unique visitors, views, clones, top referrers, top
  paths) for repos you own via the GitHub API
- Pulls stargazers, watchers, and forkers — the only repo activity GitHub
  attaches real usernames to
- Saves a snapshot to a local history file each run, so GitHub's 14-day
  traffic retention window doesn't erase your data over time
- Diffs the new snapshot against the last one and emails you only when
  something actually changed

## What it can't do (by GitHub's design, not a limitation of this tool)

GitHub does not expose *who* viewed a profile or repository page — only
aggregate counts. No tool, including this one, can show individual
identities behind a page view. This project is upfront about that; it only
surfaces real usernames where GitHub actually attaches them (stars,
watches, forks).

## How it works

```
watch_repos.py          – fetches data via GitHub's REST API, diffs
                           against history/, sends email via SMTP
.github/workflows/       – GitHub Actions workflow that runs the script
  repo-watcher.yml         hourly (configurable) and commits history back
```

No external services, no paid APIs — just the GitHub REST API and plain
SMTP for email.

## Running your own copy

See `SETUP.md` for the private-repo setup guide, including which secrets
to configure and how to keep your token/traffic data from ever becoming
public.
