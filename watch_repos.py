#!/usr/bin/env python3
"""
GitHub Repo Watcher
--------------------
Polls traffic stats (views/clones/referrers/paths) and identity-level
activity (stargazers/watchers/forkers) for repos you own, keeps a local
JSON history (so GitHub's 14-day traffic window doesn't lose data), and
emails you a summary whenever something new shows up.

Required environment variables (set as GitHub Actions secrets):
  GH_TOKEN        - Personal access token with 'repo' scope (push access
                     to the repos you want traffic stats for)
  GH_REPOS        - Comma-separated "owner/repo" list, e.g.
                     "yourname/repo1,yourname/repo2"
  SMTP_HOST       - e.g. smtp.gmail.com
  SMTP_PORT       - e.g. 587
  SMTP_USER       - your SMTP username / email address
  SMTP_PASS       - your SMTP password or app password
  EMAIL_TO        - where to send the alert (can be same as SMTP_USER)
  EMAIL_FROM      - optional, defaults to SMTP_USER
"""

import os
import json
import smtplib
import sys
from email.mime.text import MIMEText
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

API_ROOT = "https://api.github.com"
HISTORY_DIR = Path("history")
HISTORY_DIR.mkdir(exist_ok=True)


def gh_request(path, token):
    url = f"{API_ROOT}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-repo-watcher-script",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  [warn] {e.code} on {path}: {body[:200]}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"  [warn] network error on {path}: {e}", file=sys.stderr)
        return None


def fetch_repo_snapshot(owner_repo, token):
    """Pull traffic + stargazers/watchers/forkers for one repo."""
    views = gh_request(f"/repos/{owner_repo}/traffic/views", token) or {}
    clones = gh_request(f"/repos/{owner_repo}/traffic/clones", token) or {}
    referrers = gh_request(f"/repos/{owner_repo}/traffic/popular/referrers", token) or []
    paths = gh_request(f"/repos/{owner_repo}/traffic/popular/paths", token) or []

    stargazers = gh_request(f"/repos/{owner_repo}/stargazers", token) or []
    watchers = gh_request(f"/repos/{owner_repo}/subscribers", token) or []
    forks = gh_request(f"/repos/{owner_repo}/forks", token) or []

    def usernames(items):
        return sorted({i.get("login") for i in items if isinstance(i, dict) and i.get("login")})

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "traffic": {
            "views_total": views.get("count", 0),
            "views_unique": views.get("uniques", 0),
            "clones_total": clones.get("count", 0),
            "clones_unique": clones.get("uniques", 0),
            "referrers": {r.get("referrer", "?"): r.get("count", 0) for r in referrers if isinstance(r, dict)},
            "popular_paths": {p.get("path", "?"): p.get("count", 0) for p in paths if isinstance(p, dict)},
        },
        "stargazers": usernames(stargazers),
        "watchers": usernames(watchers),
        "forkers": usernames(forks),
    }


def history_path(owner_repo):
    safe = owner_repo.replace("/", "__")
    return HISTORY_DIR / f"{safe}.json"


def load_previous(owner_repo):
    p = history_path(owner_repo)
    if p.exists():
        return json.loads(p.read_text())
    return None


def save_snapshot(owner_repo, snapshot):
    history_path(owner_repo).write_text(json.dumps(snapshot, indent=2))


def diff_snapshots(owner_repo, prev, curr):
    """Return a human-readable list of what's new, or [] if nothing changed."""
    lines = []

    if prev is None:
        lines.append(f"First run for {owner_repo} — baseline recorded, no diff yet.")
        return lines

    pt, ct = prev["traffic"], curr["traffic"]
    if ct["views_unique"] > pt["views_unique"] or ct["views_total"] > pt["views_total"]:
        lines.append(
            f"👀 Views: {pt['views_total']} → {ct['views_total']} total "
            f"({pt['views_unique']} → {ct['views_unique']} unique visitors, last 14 days)"
        )
    if ct["clones_unique"] > pt["clones_unique"] or ct["clones_total"] > pt["clones_total"]:
        lines.append(
            f"⬇️  Clones: {pt['clones_total']} → {ct['clones_total']} total "
            f"({pt['clones_unique']} → {ct['clones_unique']} unique cloners, last 14 days)"
        )

    new_referrers = set(ct["referrers"]) - set(pt["referrers"])
    if new_referrers:
        lines.append(f"🔗 New referrers seen: {', '.join(sorted(new_referrers))}")

    for kind, emoji in (("stargazers", "⭐"), ("watchers", "👁️"), ("forkers", "🍴")):
        new_people = sorted(set(curr[kind]) - set(prev[kind]))
        if new_people:
            lines.append(f"{emoji} New {kind}: {', '.join(new_people)}")

    return lines


def send_email(subject, body):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    to_addr = os.environ["EMAIL_TO"]
    from_addr = os.environ.get("EMAIL_FROM", user)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())


def main():
    token = os.environ.get("GH_TOKEN")
    repos_env = os.environ.get("GH_REPOS", "")
    if not token or not repos_env:
        print("GH_TOKEN and GH_REPOS must be set.", file=sys.stderr)
        sys.exit(1)

    repos = [r.strip() for r in repos_env.split(",") if r.strip()]
    all_new_lines = []

    for owner_repo in repos:
        print(f"Checking {owner_repo} ...")
        prev = load_previous(owner_repo)
        curr = fetch_repo_snapshot(owner_repo, token)
        diff_lines = diff_snapshots(owner_repo, prev, curr)
        save_snapshot(owner_repo, curr)

        if diff_lines:
            all_new_lines.append(f"\n=== {owner_repo} ===")
            all_new_lines.extend(diff_lines)

    if not all_new_lines:
        print("No changes since last run. No email sent.")
        return

    body = "New GitHub repo activity detected:\n" + "\n".join(all_new_lines)
    body += "\n\n(Note: 'views' are aggregate counts from GitHub — GitHub never reveals individual viewer identities. Only stars/watches/forks come with usernames.)"
    print(body)

    # Only attempt email if SMTP secrets are present (lets you test without email configured)
    if all(k in os.environ for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "EMAIL_TO")):
        send_email("GitHub Repo Watcher: new activity", body)
        print("Email sent.")
    else:
        print("SMTP secrets not fully set — skipped sending email.")


if __name__ == "__main__":
    main()
