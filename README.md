# Audit_User_Agent — Bizzal daily content reviewer

An automated "editor-in-chief" that runs once a day on GitHub Actions, reviews
every Bizzal property, and files its critique as GitHub issues. **Advisory only —
it never edits or publishes anything.**

## What it reviews

Defined in [`reviewer/targets.yml`](reviewer/targets.yml):

| Property | Live | Source repo |
| --- | --- | --- |
| Bizzal Games — YouTube | [@Bizzal_Games](https://www.youtube.com/@Bizzal_Games) | `Bizzal-Games-YT-PUB` |
| Bizzal Games — Instagram | [@bizzalgames70](https://www.instagram.com/bizzalgames70/) | `Bizzal-Games-YT-PUB` |
| It's Already Written | [blog](https://bizzal70.github.io/itsalreadywritten/) · [@ItsAlrdyWritten](https://x.com/ItsAlrdyWritten) | `itsalreadywritten` |
| It's Already Priced | [blog](https://bizzal70.github.io/itsalreadypriced/) · [@ItsAlreadyPrice](https://x.com/ItsAlreadyPrice) | `itsalreadypriced` |
| It's Already When | [blog](https://bizzal70.github.io/itsalreadywhen/) · [@itsalreadywhen](https://x.com/itsalreadywhen) | `itsalreadywhen` |

## How it works

1. **Collect** — scrapes each live URL via Bright Data (audience-facing view) and
   reads the newest generated content from each source repo via the GitHub API.
2. **Judge** — Claude scores the content against a per-channel rubric
   (`reviewer/rubrics/`) and returns scores, findings, and the single
   highest-leverage improvement.
3. **Report**
   - a **detail issue** per property in its own repo (via `BIZZAL_REVIEW_PAT`),
     next to the code that produced it — one stable issue, appended daily;
   - a **digest issue** in this repo (via the default `GITHUB_TOKEN`, authored by
     `github-actions[bot]`) — this is the one GitHub **emails you**, and it links
     out to every detail issue.

Everything degrades gracefully: a failed scrape or one bad property is reported,
not fatal.

## Secrets / variables to set

Repo → Settings → Secrets and variables → Actions.

**Secrets (required):**
- `ANTHROPIC_API_KEY` — Claude API key (the judge).
- `BRIGHTDATA_API_KEY` — Bright Data token (live scraping).
- `BIZZAL_REVIEW_PAT` — fine-grained PAT with `issues:write` on all five repos
  (files the per-repo detail issues). Without it, only the digest is produced.

**Variables (optional):**
- `REVIEW_MODEL` — defaults to `claude-sonnet-5`; set `claude-opus-4-8` for the
  sharpest critique.
- `BRIGHTDATA_ZONE` — Web Unlocker zone name; defaults to `web_unlocker`.

## Run it

- Scheduled: 13:00 UTC daily.
- Manual: Actions → **daily-content-review** → *Run workflow* (optionally scope to
  one property by id).
- Local debug: `REVIEW_ONLY=itsalreadypriced python -m reviewer.run`
