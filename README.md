# GitHub Repo Watcher

A small tool that tracks activity on repositories you own — traffic stats
(views, clones, referrers) and identity-level events (new stargazers,
watchers, forkers) — and emails you a summary when something changes.
Runs automatically on a schedule using GitHub Actions.

## What it does

- Pulls traffic data (unique visitors, views, clones, top referrers, top
  paths) for repos you own via the GitHub API
- Pulls stargazers, watchers, and forkers — the only repo activity GitHub
  attaches real usernames to
- Saves a snapshot to a history file each run, so GitHub's 14-day traffic
  retention window doesn't erase your data over time
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

---

## Running your own copy

This repo is safe to fork or copy for reference, but **run your working
copy in a separate, private repository** — not here. The workflow commits
a `history/` folder containing your real traffic numbers and the usernames
of anyone who starred, watched, or forked your repos. That's fine for you
to see privately; it's not something to publish alongside this demo.

### 1. Create your own private repo

On GitHub: **New repository** → give it any name → set
**Visibility: Private** → Create.

### 2. Copy these files into it

From this repo, copy over:
- `watch_repos.py`
- `.github/workflows/repo-watcher.yml`
- `.gitignore`

You can do this with GitHub's web UI (Add file → Create new file, typing
`.github/workflows/repo-watcher.yml` as the filename auto-creates the
folders), or by cloning both repos locally and copying the files with
your file explorer or `cp`/`copy`.

**Make sure `.gitignore` does *not* include a `history/` line** in your
private repo — this demo repo excludes `history/` on purpose (so no real
data ever lands here), but your private copy needs to track it so the
workflow can commit snapshots over time.

### 3. Create a fine-grained Personal Access Token

This lets the script read traffic data for your repos.

1. GitHub → click your profile picture → **Settings**
2. Left sidebar → **Developer settings** → **Personal access tokens** →
   **Fine-grained tokens** → **Generate new token**
3. Set:
   - **Token name**: anything, e.g. `repo-watcher-token`
   - **Expiration**: 90 days is a good default (you'll rotate it periodically)
   - **Repository access**: "Only select repositories" → choose the
     specific repo(s) you want watched
   - **Permissions → Repository permissions**:
     - **Administration**: Read-only (required for traffic stats)
     - **Metadata**: Read-only (usually auto-selected)
4. **Generate token** → copy it immediately, GitHub only shows it once

### 4. Get an email app password

Gmail and most providers block plain password login for scripts — you
need a separate app password.

**Gmail:**
1. Turn on **2-Step Verification** if it isn't already on:
   https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords
3. Name it anything (e.g. `repo watcher`) → **Create**
4. Copy the 16-character code shown — this is your `SMTP_PASS`, not your
   normal Gmail password

**Outlook/Hotmail:** similar app-password flow from your Microsoft account
security settings; use `smtp-mail.outlook.com` as the host.

| Provider | SMTP Host | Port |
|---|---|---|
| Gmail | `smtp.gmail.com` | `587` |
| Outlook/Hotmail | `smtp-mail.outlook.com` | `587` |
| Yahoo | `smtp.mail.yahoo.com` | `587` |
| iCloud | `smtp.mail.me.com` | `587` |

### 5. Add repository secrets

In your **private** repo → **Settings** → **Secrets and variables** →
**Actions** → **New repository secret**. Add each of these:

| Secret name | Value |
|---|---|
| `WATCHER_GH_TOKEN` | the fine-grained PAT from step 3 |
| `WATCHER_GH_REPOS` | comma-separated `owner/repo` list, e.g. `you/repo1,you/repo2` |
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | your email address |
| `SMTP_PASS` | the app password from step 4 (not your real password) |
| `EMAIL_TO` | where you want alerts sent |
| `EMAIL_FROM` | can just repeat your email address here too |

### 6. Run it for the first time

1. Go to your repo's **Actions** tab
2. Click **"Repo Watcher"** in the left sidebar
3. Click **Run workflow** → pick your default branch → **Run workflow**
4. Wait ~15–30 seconds, then refresh and click into the run to check the logs

The **first run only records a baseline** — no email yet, since there's
nothing to compare against. From the second run onward (whether triggered
manually again or by the hourly schedule), you'll get an email only when
something actually changed: a new star, a new watcher, a new fork, or a
jump in view/clone counts.

### 7. Adjust the schedule (optional)

The workflow runs every hour by default. To change that, edit the `cron`
line in `.github/workflows/repo-watcher.yml`:

```yaml
schedule:
  - cron: "0 * * * *"      # every hour
  # - cron: "0 */6 * * *"  # every 6 hours
  # - cron: "0 9 * * *"    # once a day at 9am UTC
```

---

## Safety notes for your private copy

- **Keep it private.** Public repos allow anyone to fork or open a PR,
  which is a common way GitHub Actions secrets get exfiltrated. Secrets
  themselves stay encrypted either way, but your traffic history and
  visitor usernames don't need to be public.
- **Scope your token narrowly** — select only the specific repos you want
  watched, not all-repo access.
- **Set a token expiration** rather than "no expiration," so you're
  nudged to rotate it periodically.
- **Revoke immediately** from Settings → Developer settings → Personal
  access tokens if you ever suspect the token leaked.
