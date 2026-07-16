# Audit_User_Agent — the brain of the Bizzal content machine

Three agents that run daily on GitHub Actions across every Bizzal channel that
touches a viewer (YouTube, Instagram, and the three blogs + their X accounts).

**Advisory only — none of them ever edit or publish your content.** They read,
measure, and critique; you (or a PR) act on it.

| Time (UTC) | Agent | Arc | What it answers |
| --- | --- | --- | --- |
| 11:00 | [**scout**](#content-scout--the-source-arc) | `source` | *What should we make next?* |
| 12:00 | [**measure**](#viewer-metrics--the-measure-arc) | `measure` | *What did viewers actually do?* |
| 13:00 | [**reviewer**](#content-reviewer--the-review-arc) | `review` | *Was what we published any good?* |

They're deliberately ordered: scout gathers opportunities, measure pulls real
numbers, then the reviewer critiques. Everything degrades gracefully — a dead
feed, a missing key, or one bad property is reported, never fatal.

```
scout/     feeds.yml → fetch_feeds → rank (Claude) → opportunities/*.json + digest issue
measure/   collect_youtube (Data API) + collect_instagram (published file) → metrics/*.json + digest
reviewer/  targets.yml → collect → judge (Claude + rubrics) → per-repo issues + digest
```

---

## Content reviewer — the `review` arc

Scores every property against a per-channel rubric and files the critique as
GitHub issues. Targets live in [`reviewer/targets.yml`](reviewer/targets.yml).

| Property | Live source | Repo source | Rubric |
| --- | --- | --- | --- |
| Bizzal Games — YouTube | RSS feed for [@Bizzal_Games](https://www.youtube.com/@Bizzal_Games) | — (Supabase-driven) | `youtube` |
| Bizzal Games — Instagram | published insights (see below) | — | `instagram` |
| It's Already Written | blog fetch · X *deferred* | `_posts` | `blog` |
| It's Already Priced | blog fetch · X *deferred* | `_posts` / `_field_notes` | `blog` |
| It's Already When | blog fetch · X *deferred* | `_posts` / `_field_notes` | `blog` |

*deferred* = no free way to read it (login/bot walls). The property is still
reviewed on its other sources, and the judge is told **not** to score criteria it
couldn't actually see — an unavailable source never drags the score down.

**Instagram is fully reviewed.** IG can't be read for free, and personal-account
secrets don't cross repos — so `Bizzal-Games-YT-PUB` (where the IG token already
lives and posts) collects insights into its `data/metrics/instagram.json`, and
[`reviewer/instagram.py`](reviewer/instagram.py) reads that published file. No IG
secret is needed in this repo.

**How it reports**
- a **detail issue** per property *in its own repo* (via `BIZZAL_REVIEW_PAT`), so
  findings sit next to the code that produced them — one stable issue, appended daily;
- a **digest issue** here, authored by `github-actions[bot]` via the default
  `GITHUB_TOKEN` — that authorship is deliberate: GitHub never emails you about
  your *own* PAT-authored actions, so the bot-authored digest is the one that
  actually reaches your inbox. It links out to every detail issue.

**Rubrics** live in [`reviewer/rubrics/`](reviewer/rubrics/):
`youtube` · `instagram` · `blog` · `blog_growth`

`blog_growth` is an alternate lens — it ignores editorial quality and scores
purely on **clicks (CTR) and follower conversion**. Apply any rubric to any run
with the `rubric` input (see below).

---

## Viewer metrics — the `measure` arc

Pulls real numbers so review stops being opinion and starts being evidence.
Writes a time-series to `measure/metrics/<channel>.json` (committed daily) and
files a metrics digest issue.

| Channel | Source | Metrics |
| --- | --- | --- |
| YouTube | Data API v3 (uploads playlist → `videos`) | views, likes, comments |
| Instagram | `data/metrics/instagram.json` published by `Bizzal-Games-YT-PUB` | reach, views, likes, comments, saves |

Video IDs come from the **uploads playlist via the Data API**, not the public RSS
feed — the feed 404s intermittently even from Actions.

**Not yet wired:** YouTube retention/CTR/watch-time (needs the Analytics API +
OAuth) and blog analytics (GitHub Pages has none; GoatCounter is the plan).

---

## Content scout — the `source` arc

Unifies content discovery. Where the reviewer critiques what's published, the
scout finds what to make next.

- [`scout/feeds.yml`](scout/feeds.yml) — one registry of every RSS/Atom/social
  feed, tagged by topic (`ttrpg` / `crypto` / `cyber`). A feed shared across beats
  (e.g. The Hacker News → crypto + cyber) is fetched **once** and routed to every
  channel that wants it.
- **Per-channel opportunities** — ranked by Claude into concrete title/hook ideas
  with a why-now and a source link.
- **Cross-channel plays** — one story that feeds 2+ channels (a supply-chain hack
  for crypto-security *and* cyber), with the per-channel spin. This is the point of
  unifying: the four pipelines were previously blind to each other.

**Output:** machine-readable queues at `scout/opportunities/<channel>.json` (for a
pipeline's `create` step to consume) plus a daily digest issue. Advisory today —
not yet wired into the pipelines' generation step.

---

## Secrets / variables

Repo → Settings → Secrets and variables → Actions. `bizzal70` is a **personal
(non-org) account, so secrets do not carry over from your other repos** — each
must be added here, even if the same value already exists elsewhere.

**Secrets**

| Secret | Used by | Required? |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | reviewer + scout (the judge/ranker) | **yes** |
| `BIZZAL_REVIEW_PAT` | reviewer — fine-grained PAT, `issues:write` on all five repos | yes for per-repo detail issues; without it you still get the digest |
| `BIZZAL_YT_DATA_API_KEY` | measure — YouTube Data API v3 read key (`AIza…`) | yes for YouTube metrics |

No Instagram or scraper key is needed here — IG metrics arrive via the games
repo's published file, and all other collection is key-free.

**Variables (optional)**

| Variable | Default | Notes |
| --- | --- | --- |
| `REVIEW_MODEL` | `claude-sonnet-5` | set `claude-opus-4-8` for the sharpest critique |
| `SCOUT_LOOKBACK_DAYS` | `3` | how far back the scout reads feeds |
| `YT_CHANNEL_ID` | `UCn8fIswollQTSAJYkAshjyw` | @Bizzal_Games |

> Unset Actions variables arrive as an **empty string**, not as absent — the code
> coalesces blanks to the defaults above with `or`, not `dict.get(k, default)`.

---

## Run it

| Workflow | Schedule | Manual inputs |
| --- | --- | --- |
| `daily-content-scout` | 11:00 UTC | — |
| `daily-viewer-metrics` | 12:00 UTC | — |
| `daily-content-review` | 13:00 UTC | `only`, `rubric` |

**Reviewer inputs**
- `only` — one property id or a **comma-separated list**; blank = all.
  Ids: `bizzal-games-youtube`, `bizzal-games-instagram`, `itsalreadywritten`,
  `itsalreadypriced`, `itsalreadywhen`
- `rubric` — override the rubric for every reviewed property; blank = each
  property's default. e.g. `blog_growth` for a clicks/followers pass.

```bash
# score just the crypto blog on the growth lens
gh api -X POST repos/bizzal70/Audit_User_Agent/actions/workflows/daily-review.yml/dispatches \
  -f ref=main -f "inputs[only]=itsalreadypriced" -f "inputs[rubric]=blog_growth"
```

**Local debug**
```bash
REVIEW_ONLY=itsalreadypriced python -m reviewer.run
python -m scout.run
python -m measure.run
```
