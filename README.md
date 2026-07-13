# Audit_User_Agent — Bizzal daily content reviewer

An automated "editor-in-chief" that runs once a day on GitHub Actions, reviews
every Bizzal property, and files its critique as GitHub issues. **Advisory only —
it never edits or publishes anything.**

## What it reviews

Defined in [`reviewer/targets.yml`](reviewer/targets.yml):

| Property | Live source (free) | Repo source |
| --- | --- | --- |
| Bizzal Games — YouTube | RSS feed for [@Bizzal_Games](https://www.youtube.com/@Bizzal_Games) | — (Supabase-driven) |
| Bizzal Games — Instagram | deferred* | — |
| It's Already Written | blog fetch · X deferred* | `_posts` |
| It's Already Priced | blog fetch · X deferred* | `_posts` / `_field_notes` |
| It's Already When | blog fetch · X deferred* | `_posts` / `_field_notes` |

\* **deferred** = can't be read for free (login/bot walls). The property is still
reviewed on its other sources. Add a paid scraper later to light these up.

## How it works

1. **Collect** — key-free: public blogs via plain HTTP (HTML stripped to text),
   YouTube via its public RSS feed, and the newest generated content from each
   source repo via the GitHub API. Instagram/X are deferred.
2. **Judge** — Claude scores the content against a per-channel rubric
   (`reviewer/rubrics/`) and returns scores, findings, and the single
   highest-leverage improvement.
3. **Report**
   - a **detail issue** per property in its own repo (via `BIZZAL_REVIEW_PAT`),
     next to the code that produced it — one stable issue, appended daily;
   - a **digest issue** in this repo (via the default `GITHUB_TOKEN`, authored by
     `github-actions[bot]`) — this is the one GitHub **emails you**, and it links
     out to every detail issue.

Everything degrades gracefully: a failed fetch or one bad property is reported,
not fatal.

## Secrets / variables to set

Repo → Settings → Secrets and variables → Actions. Because `bizzal70` is a
personal (non-org) account, secrets do **not** carry over from your other repos —
they must be added here.

**Secrets (required):**
- `ANTHROPIC_API_KEY` — Claude API key (the judge). Same value you use in the blog
  repos; paste it in here too.
- `BIZZAL_REVIEW_PAT` — fine-grained PAT with `issues:write` on all five repos
  (files the per-repo detail issues). Without it, only the digest is produced.

**No scraper key needed** — collection is key-free.

**Variables (optional):**
- `REVIEW_MODEL` — defaults to `claude-sonnet-5`; set `claude-opus-4-8` for the
  sharpest critique.

## Run it

- Scheduled: 13:00 UTC daily.
- Manual: Actions → **daily-content-review** → *Run workflow* (optionally scope to
  one property by id).
- Local debug: `REVIEW_ONLY=itsalreadypriced python -m reviewer.run`
