# CLAUDE.md

## Project Overview
Three daily, advisory-only agents that audit the user's whole content portfolio (Bizzal Games YouTube/Instagram + the three "It's Already *" blogs): **scout** (what should we make next?), **measure** (what did viewers actually do?), **review** (was what we published any good?). Run order is deliberate: scout 11:00 UTC → measure 12:00 UTC → review 13:00 UTC. **None of the three ever edit or publish content** — they read, score, and file GitHub issues; a human (or a future PR) acts on the output. Confirmed live: 4+ consecutive days of successful scheduled runs and three actively-growing digest issues (21-36 comments each) as of this check.

## Tech Stack
- Claude API (`anthropic` SDK) — default model `claude-sonnet-5` (hardcoded fallback in `reviewer/judge.py` and `scout/rank.py`), overridable via the `REVIEW_MODEL` repo variable
- YouTube: free public RSS (reviewer's content read) + YouTube Data API v3 with `BIZZAL_YT_DATA_API_KEY` (measure's real stats)
- Instagram: **no IG API call in this repo at all** — both `reviewer/instagram.py` and `measure/collect_instagram.py` read a JSON file already published by the sibling repo `Bizzal-Games-YT-PUB`, where the actual IG token lives
- Blogs: plain HTTP GET + HTML-strip for public pages, plus GitHub Contents API reads of each blog repo's own source
- X/Twitter: **not fetched anywhere** — every property's X account is `method: deferred` in `reviewer/targets.yml` ("no free way to read it"); the judge is explicitly told not to penalize for missing X data
- Delivery: GitHub Issues only, no direct email-sending code — bot-authored (`GITHUB_TOKEN`) digest issues are deliberately used because GitHub emails the owner for actions *not* authored by their own PAT, so this is how a digest reaches the inbox

## Commands
No local dev loop — cloud-only, no persistent local clone.
```bash
# Manually run the scout (content opportunities)
gh workflow run daily-scout.yml

# Manually run measure (viewer metrics)
gh workflow run daily-measure.yml

# Manually run the reviewer, optionally scoped/rubric-overridden
gh workflow run daily-review.yml -f only=<property_id> -f rubric=<rubric_name>
```

## Code Style
- Every collector function degrades gracefully (catches, prints/logs, returns `None`) rather than raising — "one dead feed / bad property / missing secret must never fail the whole run" is enforced at the per-property, per-channel, and per-feed level throughout `scout/` and `reviewer/`. Match this pattern in any new collector.
- `REVIEW_MODEL` and other optional repo variables are read with `or "default"`, not `dict.get(key, default)` — the README and code both explicitly call out that unset Actions vars arrive as `""`.

## Testing
- No test suite — validate via `workflow_dispatch` and read the actual digest issue or per-property detail issue produced.
- The reviewer explicitly skips a property rather than fabricating a score when there's no live source and no repo content available — don't "fix" a skip by forcing a score.

## Repository Etiquette
- Only doc is `README.md` (comprehensive — architecture, per-property source/rubric table, secrets table, manual dispatch examples); no `docs/` directory.
- This repo has cross-repo write access to the blog/YT repos via `BIZZAL_REVIEW_PAT` (issues only) — treat any change to that PAT's scope or usage with extra care since it touches other repos' issue trackers.

## Architecture Notes
- `scout/run.py` — orchestrator: loads `scout/feeds.yml` (~20 RSS/Atom feeds tagged ttrpg/crypto/cyber), calls `rank.py` (two Claude passes: per-channel top-5 opportunities + cross-channel "plays"), writes `scout/opportunities/<channel>.json` + `_cross_channel.json`, publishes a digest issue
- `measure/run.py` — calls `collect_youtube.py` (Data API, via uploads playlist — explicitly NOT the public RSS feed, which "404s intermittently even from Actions") + `collect_instagram.py`, appends a dated snapshot to `measure/metrics/<channel>.json` (last 180 entries kept)
- `reviewer/run.py` — for each property in `reviewer/targets.yml`, calls `collect.py` (live public sources + the property's own repo source via Contents API) then `judge.py` (Claude scoring against a rubric in `reviewer/rubrics/*.md`), publishes both a digest issue here and a per-property detail issue in the source repo (via `BIZZAL_REVIEW_PAT`)
- `reviewer/targets.yml` — single source of truth for the 5 reviewed properties, each with live sources / source repo / issue repo / rubric
- State: `scout/opportunities/*.json` and `measure/metrics/*.json` are committed daily; the reviewer has **no committed state file** — its memory is the persistent GitHub issue thread itself (one stable issue per property, found by exact title match, so it's idempotent across runs)

## Boundaries — What NOT To Do
- **Cloud-only, no exceptions** — no persistent local clone of this repo exists or should exist.
- **Advisory only, always.** Nothing in this repo may auto-edit or auto-publish content on any property — this is stated in the README and directly in both `judge.py`'s and `rank.py`'s system prompts. If asked to "just fix the flagged issue automatically," that's out of scope for this repo by design; it proposes, a human/PR acts.
- **Never duplicate the Instagram token into this repo.** IG credentials deliberately stay in `Bizzal-Games-YT-PUB` (personal GitHub accounts don't share secrets across repos); this repo only ever reads the *published* metrics JSON, never holds IG credentials itself.
- **Known inconsistency, not yet fixed:** `reviewer/instagram.py` was fixed to read via the GitHub Contents API (not `raw.githubusercontent.com`) after the raw CDN's caching served stale captions and caused phantom "truncated caption" defects in judge output. **`measure/collect_instagram.py` was not given the same fix** — it still reads `raw.githubusercontent.com` directly. Low-stakes today (measure only uses `caption` for a 50-char digest truncation, not judged content) but if this module's use of caption data expands, apply the same GitHub-Contents-API + no-cache-header fix used in `reviewer/instagram.py`.
- **Never fabricate a judge score for unreviewable content** — if a property has no live source and no repo content, skip it; don't let a future change silently default to a middling score instead.

## Workflow Preferences
- For anything touching `judge.py`'s rubric logic or scoring prompts, validate via a scoped manual run (`-f only=<property>`) before trusting the change against all 5 properties at once.
- This repo files issues into other repos via `BIZZAL_REVIEW_PAT` — treat any change to that cross-repo behavior as touching shared state, not just this repo.

## Environment / Secrets
- `ANTHROPIC_API_KEY` — Claude API key, used by both the reviewer's judge and the scout's ranker
- `GITHUB_TOKEN` (built-in) — commits metrics/opportunities, authors the bot-authored digest issues (this authorship choice is what makes GitHub email the owner)
- `BIZZAL_YT_DATA_API_KEY` — YouTube Data API v3 key for measure's real stats; degrades gracefully (skips) if absent
- `BIZZAL_REVIEW_PAT` — fine-grained PAT with cross-repo `issues:write`, used to file per-property detail issues in each source repo; optional — without it, only the digest issue in this repo is produced
- `REVIEW_MODEL` (repo variable, not secret) — overrides the Claude model id for both scout and review; README suggests `claude-opus-4-8` for "the sharpest critique"
- `SCOUT_LOOKBACK_DAYS` (repo variable) — default 3
- `YT_CHANNEL_ID` (repo variable) — default `UCn8fIswollQTSAJYkAshjyw` (@Bizzal_Games)
