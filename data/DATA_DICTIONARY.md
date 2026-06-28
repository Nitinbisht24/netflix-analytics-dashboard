# Data Dictionary

This project combines **two genuinely different datasets** that should never be confused with each other. Keeping them separate — and labeling which is which everywhere in the UI — is the whole point of this document.

| | `movie_market.csv` | `netflix_engagement_report.csv` |
|---|---|---|
| **What it is** | ~21,800-row global movie catalogue (TMDB-style metadata: budget, box-office revenue, ratings, popularity) | 174 real rows compiled from Netflix's own published viewership data |
| **What it's good for** | Industry benchmarking — which genres/markets/languages tend to be profitable | Actual Netflix audience behavior — what people really watched |
| **What it's NOT** | Netflix's internal catalogue or financials | A complete picture of everything on Netflix (Netflix has 18,000+ titles; this tracks ~174 of the most-discussed ones) |

---

## 1. `data/raw/movie_market.csv`

A generic movie-metadata export (TMDB-style schema) used as a **market-intelligence benchmark**. Most of these titles were never produced or financed by Netflix — some aren't even available on Netflix. The analytics in the "Movie Market" half of the dashboard answer a content-strategy question: *"based on how movies generally perform, what genres/markets/budgets tend to pay off?"* — not *"how is Netflix's own catalogue performing"* (that's what section 2 is for).

| Column | Type | Notes |
|---|---|---|
| `show_id` | int | Original source ID, not re-used for anything |
| `title` | str | |
| `type` | str | 100% `"Movie"` in this export — despite the "Netflix" framing, no TV shows are present in this file |
| `director`, `cast` | str | Comma-separated |
| `country` | str | Comma-separated for co-productions; exploded to one row per country in the ETL layer |
| `release_year` | int | |
| `genres` | str | Comma-separated; `primary_genre` (first listed) is added by the ETL layer |
| `language` | str | ISO-ish 2-letter code as exported (`en`, `hi`, `ko`, …) |
| `description` | str | Synopsis; used as part of the recommender's text corpus |
| `popularity`, `vote_count`, `vote_average` | float/int | TMDB-style engagement/quality proxies — **not** Netflix viewership |
| `budget`, `revenue` | float (USD) | Theatrical/production box-office economics, where TMDB had them |

### Known data-quality issues (and how they're handled)

All of the below are handled in `core/etl.py`, not by silently editing the raw CSV — the raw file is left untouched so every transformation is auditable in code.

1. **A `rating` column duplicating `vote_average` byte-for-byte.** Dropped — clearly an upstream export bug, not a second signal.
2. **A `duration` column that is 100% null.** Dropped rather than imputed — there's nothing to impute from.
3. **`budget`/`revenue` are `0`, not null, for ~65–70% of titles.** Mostly smaller/library titles TMDB never priced. ROI/profit are computed **only** where a reliable budget exists (see #4) — every other title's ROI is `null`, never a misleading `0%`.
4. **~150 titles have a budget under $50,000 — several literally `$1`.** These are placeholder/error values, not real economics: dividing revenue by a $1 budget produces ROI in the hundreds-of-thousands-of-percent range and silently dominates every genre/language average downstream. The fix: a **$50,000 minimum-reliable-budget floor** (`has_financials` flag in `core/etl.py`), well below even no-budget indie filmmaking, so it only screens out data errors — not genuine micro-budget titles. Genre ROI figures became sane (e.g. Horror's ROI dropped from a meaningless +39,000% to a believable +367%, which matches Horror's well-known reputation as the highest-ROI mainstream genre) immediately after this fix.
5. **A small slice (~1%, ~500 rows before country-explode) of titles are explicit/pornographic content mixed into the export** (no `adult` flag column was present to filter on upstream). A Netflix-style content-strategy dashboard has no legitimate use for this content, so a conservative keyword filter removes it in `core/etl.py` *before* anything else touches the data — it never reaches the database, the recommender index, or search. The filter has some false positives (a few mainstream dramas *about* the adult industry, e.g. biopics, get caught too); for this kind of project, over-exclusion is the right trade-off.

---

## 2. `data/raw/netflix_engagement_report.csv`

174 rows of **genuinely real** data, manually compiled from Netflix's own published bi-annual **"What We Watched: A Netflix Engagement Report"** series (covering H1 2023 through H2 2025) plus the **all-time most-watched lists** Netflix publishes on Tudum (cross-referenced via Wikipedia's "List of most-watched Netflix original programming"), and corroborating trade press (Variety, TV Guide, Digital Trends, NME, TV Blackbox, What's-on-Netflix, nScreenMedia) covering each report's release.

**No figure in this file is estimated or invented.** Where Netflix didn't publish a number for a title, the field is left blank — never filled in with a guess.

| Column | Type | Notes |
|---|---|---|
| `title` | str | |
| `content_type` | str | `Movie`, `TV Show`, `Live Event`, or `Special` |
| `primary_genre` | str | Best-effort classification by the dataset compiler (this app), aligned to the same genre vocabulary as `movie_market.csv` so the two datasets can be compared |
| `genre_detail` | str | Free-text description, closer to how press described the title |
| `country_origin` | str | Explicitly stated where the source named it; otherwise a reasonable best-effort default from language/production context — see caveat below |
| `language` | str | Primary language |
| `report_period` | str | One of `2023-H1` … `2025-H2`, or `All-Time` (Netflix's all-time leaderboard, a different — longer and rolling — measurement window than the half-year reports) |
| `premiere_date` | date | Only populated where a source explicitly stated it |
| `hours_viewed_millions` | float | Netflix's headline "hours viewed" metric, in millions. **Not published for every title** — Netflix has changed which metric it leads with across reports |
| `views_millions` | float | Netflix's "completed-viewing-equivalent" metric (hours ÷ runtime), in millions |
| `primary_metric` | str | Which of the above two this row actually has (`hours`, `views`, or `none`) — set automatically, never both fabricated from one |
| `source` | str | Which report/article the row came from |

### Caveats specific to this dataset

1. **Country/genre tags are best-effort, not Netflix-official.** Netflix's press releases describe titles in prose ("Dear Child, from Germany"); turning that into clean categorical columns involved judgment calls for the less prominent international titles. For the major/iconic titles (Squid Game, Wednesday, Stranger Things, etc.) these are unambiguous and well-documented.
2. **"All-Time" rows are NOT additive with the per-half-year rows.** Netflix's all-time leaderboard uses a different (longer, rolling) measurement window than a single six-month report, and several titles appear in *both* an `All-Time` row and one or more per-half rows for the same underlying viewing. **Every aggregate (sum) in this app — the KPI totals, the genre breakdown, the country breakdown — explicitly excludes `All-Time` rows** to avoid double-counting (see `core/database.py` and `core/engagement.py`). `All-Time` rows are only ever used for *individual* ranking (the "Most-Watched Titles" list), where mixing an all-time leader in among recent-half leaders is a normal, intuitive thing for that kind of leaderboard to do.
3. **This is a curated sample, not Netflix's full catalogue.** Netflix carries 18,000+ titles; this file tracks the ~174 that were prominent enough to appear in an official report or get cross-referenced trade coverage. Treat percentages/shares computed from it (e.g. "international content's share") as representative of *what gets reported on*, not a census.
4. **Two different metrics, never merged into one.** "Hours viewed" and "views" measure different things and Netflix hasn't published both for every title in every report. The app always labels which metric a number is, and never derives one from the other.

---

## Where this matters in the app

- **"Movie Market" nav group** (Overview, Growth, Genres, ROI, Correlations, Languages, Budget/Rev, Evolution, Forecast, Top Titles, Insights, and the Recommender) → `movie_market.csv`, market-benchmark framing.
- **"Real Netflix Data" nav group** (Engagement) → `netflix_engagement_report.csv`, genuinely-Netflix framing, with its own KPIs/insights clearly labeled as sourced from Netflix's own reports.
- The PDF/Excel export reports pull from both, each clearly labeled per-sheet/section.
