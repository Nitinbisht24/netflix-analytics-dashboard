# 🎬 Netflix Content Strategy — Analytics Pro

A full-stack content-strategy analytics platform: a Flask + SQLite backend, a dependency-free Chart.js dashboard, a content-based recommender (scikit-learn), trend forecasting, statistical significance testing (scipy), and one-click PDF/Excel executive reports — built on top of **two real, clearly-separated datasets**: a 21,800-title global movie-market catalogue used as an industry benchmark, and 174 rows of **genuine** data compiled from Netflix's own published bi-annual engagement reports.

> **This is not Netflix's internal data.** It's a portfolio-grade analytics project that combines public movie-market metadata (for market-benchmarking analytics) with Netflix's own officially published viewership figures (for the "Real Netflix Data" section). Every number's source is documented in [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) — read that file before trusting any specific figure in a presentation.

---

## What's in here

| Capability | Where |
|---|---|
| KPIs, growth trend, genre/language ROI, correlations, budget-vs-revenue regression, genre evolution over time | Movie-market dashboard |
| One-way ANOVA: *is the genre-ROI gap statistically significant, or just noise?* | `core/analytics.py::get_genre_roi_significance` |
| Linear-trend content-volume & revenue **forecasting** with an 80% confidence band | `core/forecasting.py` |
| Content-based **recommender** ("titles like this") — TF-IDF over genre + synopsis + director, cosine similarity | `core/recommender.py` |
| Real Netflix viewership — most-watched titles, by genre, by country, half-on-half trend, all sourced from Netflix's own reports | `core/engagement.py` |
| One-click **PDF executive summary** and **multi-sheet Excel workbook** export | `core/reports.py` |
| Live title search & autocomplete | `/api/search` |
| 54 automated tests covering ETL, database, analytics, recommender, and every API route | `tests/` |

---

## Quick start

```bash
# 1. Clone / unzip, then create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py
```

Open **http://localhost:5000**. On first run, the app builds `data/processed/analytics.db` from the raw CSVs (~5-10 seconds) and warms up the recommender index — every run after that is instant.

### Run with Docker instead

```bash
docker compose up --build
```

### Run the tests

```bash
python -m unittest discover -s tests -v
```

54 tests, no test framework beyond the standard library required (also pytest-discoverable if you have it installed: `pytest tests/`).

---

## Project structure

```
netflix_analytics_pro/
├── app.py                  # Flask application factory & entrypoint
├── config.py                # Environment-driven configuration
├── core/                     # All business logic — framework-agnostic, fully unit-testable
│   ├── etl.py                  # CSV → cleaned DataFrame (the ONLY place data-cleaning decisions live)
│   ├── database.py             # SQLite schema + pre-aggregation ("build once, query fast")
│   ├── cache.py                 # In-memory TTL cache for read-heavy endpoints
│   ├── analytics.py            # Movie-market analytics: KPIs, ROI, correlations, regression, ANOVA
│   ├── engagement.py           # Real Netflix engagement-report analytics
│   ├── recommender.py          # TF-IDF + cosine-similarity content recommender
│   ├── forecasting.py          # Linear-trend forecasting
│   └── reports.py              # PDF (reportlab) / Excel (openpyxl) report builders
├── api/                      # Thin Flask blueprints — one per concern, all delegate to core/
│   ├── market.py, engagement.py, recommend.py, forecast.py, reports.py, admin.py
├── data/
│   ├── raw/                    # Immutable source CSVs (+ the script that built the engagement one)
│   ├── processed/               # Generated SQLite DB (gitignored — rebuilt on first run)
│   └── DATA_DICTIONARY.md      # Read this before quoting any number from this app
├── templates/, static/        # Server-rendered dashboard shell + vanilla JS/CSS (no build step)
├── tests/                     # 54 unittest cases across every layer
├── notebooks/                  # Standalone exploratory-analysis notebook (pandas/matplotlib)
├── Dockerfile, docker-compose.yml
└── requirements.txt
```

**Design choice:** `core/` has zero Flask imports. Every analytics function is a plain Python function that takes simple arguments and returns a dict — which is *why* the test suite can hit `core.analytics.get_kpis("All")` directly without spinning up a server, and why swapping Flask for FastAPI later would only touch `api/`.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  data/raw/*.csv  │────▶│   core/etl.py    │────▶│  core/database.py    │
│  (immutable)     │     │  clean + derive  │     │  build pre-aggregated│
└─────────────────┘     └──────────────────┘     │  SQLite tables once  │
                                                    └──────────┬───────────┘
                                                               │
                          ┌────────────────────────────────────┼─────────────────────┐
                          ▼                                    ▼                     ▼
                 core/analytics.py                    core/engagement.py     core/recommender.py
                 (movie-market stats)                  (real Netflix data)    (in-memory TF-IDF)
                          │                                    │                     │
                          └────────────────┬───────────────────┴─────────────────────┘
                                           ▼
                                   api/*.py  (Flask blueprints, cached)
                                           │
                                           ▼
                          templates/index.html + static/js/dashboard.js
                                  (Chart.js, vanilla JS, no build step)
```

Every API route is a thin wrapper: parse query params → call a `core` function → `jsonify`. All the actual logic — and all of its tests — live in `core/`, independent of Flask.

---

## Key engineering decisions worth knowing about

These came up while building this and are documented in code comments at the point they matter, but the headline versions:

1. **A $50,000 minimum-budget floor before computing ROI.** The raw movie-market export has ~150 titles with budgets under $50K (some literally `$1`) — placeholder/error values that blow up ROI into the hundreds-of-thousands-of-percent range and dominate every genre average. Filtering them fixed Horror's average ROI from a meaningless +39,000% to a believable +367% (which matches Horror's real-world reputation as the highest-ROI mainstream genre).
2. **An explicit-content filter at the ETL boundary.** The raw export (no `adult` flag column) included a small slice of pornographic titles. A keyword filter removes them before they reach the database, the recommender, or search — not just hidden in the UI.
3. **"All-Time" Netflix figures are never summed together with the per-half-year figures.** Netflix's all-time leaderboard and its six-month reports use different, overlapping measurement windows. Summing both would double-count the same viewing. Every aggregate in `core/engagement.py` / `core/database.py` explicitly excludes `All-Time` rows from sums (while still using them for individual title rankings, where that's safe).
4. **Duplicate rows from the country-explode.** Multi-country titles are exploded to one row per country for filtering — but that means a naive "top titles" query returns the same movie twice. Fixed with `SELECT DISTINCT`.
5. **Two engagement metrics, never cross-derived.** Netflix's reports mix "hours viewed" and "views" (a views-from-hours-equivalent metric) across different reports. The app tracks which metric each row actually has and never estimates one from the other.

See [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md) for the full data-quality writeup.

---

## API reference

All endpoints return JSON. Movie-market endpoints accept `?country=All` (default) or any country name from `/api/countries`.

### Movie market
| Endpoint | Description |
|---|---|
| `GET /api/kpis` | Headline KPIs |
| `GET /api/growth` | Title volume & rating trend by year |
| `GET /api/genres` | Genre volume + rating breakdown |
| `GET /api/roi-by-genre` | ROI ranked by genre |
| `GET /api/languages`, `/api/language-roi` | Language distribution & ROI |
| `GET /api/correlations` | Pearson correlation matrix (budget, revenue, rating, popularity, votes) |
| `GET /api/yearly-trend` | Budget/revenue by year + linear regression |
| `GET /api/budget-revenue-scatter` | Sampled scatter + regression line |
| `GET /api/ratings-distribution` | Histogram of ratings |
| `GET /api/country-comparison` | Cross-country comparison |
| `GET /api/genre-evolution` | Genre share over 5 time periods |
| `GET /api/top-titles?limit=10` | Top titles by popularity |
| `GET /api/search?q=...&limit=10` | Title search/autocomplete |
| `GET /api/stats/genre-roi-significance` | One-way ANOVA on genre ROI |
| `GET /api/insights` | Auto-generated natural-language insights |

### Real Netflix engagement
| Endpoint | Description |
|---|---|
| `GET /api/engagement/kpis` | Headline real-viewership KPIs |
| `GET /api/engagement/top?metric=views\|hours&content_type=All&limit=15` | Most-watched titles |
| `GET /api/engagement/by-genre`, `/by-country` | Aggregates (All-Time rows excluded — see Data Dictionary) |
| `GET /api/engagement/trend` | Half-on-half trend, 2023-H1 → 2025-H2 |
| `GET /api/engagement/insights` | Auto-generated insights |

### Recommender, forecasting, export
| Endpoint | Description |
|---|---|
| `GET /api/recommend?title=Inception&n=8` | Content-based similar titles |
| `GET /api/recommend/seed-titles?n=6` | Random popular titles for UI chips |
| `GET /api/forecast/volume`, `/revenue?country=All&periods=3` | Trend forecast + confidence band |
| `GET /api/export/pdf?country=All` | Download PDF executive summary |
| `GET /api/export/excel?country=All` | Download Excel workbook |
| `GET /api/admin/health` | Health check |
| `POST /api/admin/cache/clear`, `/api/admin/db/rebuild` | Ops endpoints |

---

## Configuration

Copy `.env.example` to `.env` to override defaults (all optional — sane defaults work out of the box):

```
PORT=5000
FLASK_DEBUG=0
CACHE_TTL_SECONDS=300
REBUILD_DB_ON_START=0
```

---

## Deployment

The dev server (`python app.py`) is fine for local use but says so itself — for anything else:

```bash
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"
```

`-w 2` (2 worker processes) is a reasonable default for this app's size. Note the in-memory cache (`core/cache.py`) and recommender index are **per-process** — with multiple gunicorn workers, each builds its own copy at startup (a few extra seconds and ~150MB RAM per worker for the TF-IDF index), and cache entries aren't shared between workers. Fine up to a handful of workers; beyond that, swap `core/cache.py` for `Flask-Caching` + Redis and move the recommender index to a shared store.

---

## Scaling further (if this outgrows a portfolio project)

- **Database**: SQLite → Postgres is a small change since all access goes through `core/database.py::get_conn()` / `q_rows()` — swap the connection and adjust the few SQLite-specific pragmas.
- **Cache**: `core/cache.py` → Flask-Caching + Redis for multi-process/multi-host deployments.
- **Recommender**: the TF-IDF matrix is rebuilt in memory on every process start; for a larger catalogue, persist the fitted vectorizer + matrix (joblib) and/or move to an approximate-nearest-neighbour index (e.g. FAISS) instead of a dense cosine-similarity scan.
- **Data refresh**: `data/raw/_build_engagement_csv.py` documents exactly how the engagement dataset was compiled — the natural next step for a production version would be re-running that research each time Netflix publishes a new report (every ~6 months) rather than hand-compiling it.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Data sources & attribution

- Movie-market dataset: TMDB-style public movie metadata (budget/revenue/ratings).
- Real Netflix engagement dataset: Netflix's own official "What We Watched: A Netflix Engagement Report" series (H1 2023 – H2 2025) and all-time most-watched lists, cross-referenced via Wikipedia's "List of most-watched Netflix original programming" and trade press (Variety, TV Guide, Digital Trends, NME, TV Blackbox, What's-on-Netflix, nScreenMedia).

Full methodology and caveats: [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md).

This is an independent analytics project and is not affiliated with, endorsed by, or sponsored by Netflix, Inc. "Netflix" is a trademark of Netflix, Inc., used here descriptively to refer to its publicly reported data.
