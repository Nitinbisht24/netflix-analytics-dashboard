# -*- coding: utf-8 -*-
"""
core/etl.py — Extract/clean/transform layer.

Two raw sources, two loaders. Raw CSVs in data/raw/ are treated as
immutable; every cleaning decision happens here so it's auditable in one
place instead of being scattered across the codebase.

1. load_movie_market()  -> data/raw/movie_market.csv
   16,000-title global movie catalogue (TMDB-style metadata: budget,
   revenue, popularity, ratings). Used as a market-intelligence benchmark
   for content-strategy decisions (which genres/languages/markets tend to
   be profitable) — NOT as Netflix's internal financials. See
   data/DATA_DICTIONARY.md for the full caveat.

2. load_engagement()    -> data/raw/netflix_engagement_report.csv
   ~170 real titles compiled from Netflix's official bi-annual "What We
   Watched" Engagement Reports + corroborating trade press. Hours/views
   are genuine published figures; blanks mean "not published", never an
   invented zero.
"""
import os
import re
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(_HERE, "data", "raw")

MOVIE_MARKET_CSV = os.path.join(RAW_DIR, "movie_market.csv")
ENGAGEMENT_CSV = os.path.join(RAW_DIR, "netflix_engagement_report.csv")

# Known data-quality issues in the raw movie_market.csv, documented here
# rather than silently patched:
#   - "rating" is a byte-for-byte duplicate of "vote_average" (upstream
#     export bug) -> dropped.
#   - "duration" is 100% null for every row -> dropped (not imputed).
#   - "budget"/"revenue" are 0 (not null) for ~65-70% of titles, mostly
#     smaller/library titles TMDB never priced -> ROI is computed only
#     where budget > 0, everything else is left as NaN, never coerced to 0.
#   - the export (no "adult" flag column) includes a small slice (~1%) of
#     explicit/pornographic titles mixed in among mainstream movies. A
#     Netflix-style content-strategy dashboard has no legitimate use for
#     that content, so it's screened out below, before anything else
#     touches the data — it never reaches the DB, the recommender index,
#     or search. This is a conservative keyword filter (some false
#     positives — a few mainstream dramas *about* the adult industry get
#     caught too — but for this kind of project over-exclusion is the
#     right trade-off).
_EXPLICIT_PATTERN = re.compile(
    r"(?i)\b(?:xxx+|hentai|porn\w*|softcore|sex\s*tape|erotic\w*|striptease|fellatio|"
    r"masturbat\w*|orgasm\w*|hardcore|gangbang|bukkake|sex\s+and\s+zen)\b"
    r"|エロ|裏垢|ハメ撮り|中出し|アダルト(?:ビデオ)?|AV(?:男優|女優)"
)


def _drop_explicit_content(df: pd.DataFrame) -> pd.DataFrame:
    title_hit = df["title"].fillna("").str.contains(_EXPLICIT_PATTERN, regex=True)
    desc_hit = df["description"].fillna("").str.contains(_EXPLICIT_PATTERN, regex=True)
    return df[~(title_hit | desc_hit)].copy()



def load_movie_market() -> pd.DataFrame:
    """Load + clean the movie market catalogue. One row per (title, country)."""
    df = pd.read_csv(MOVIE_MARKET_CSV)
    df = _drop_explicit_content(df)

    df = df.drop(columns=[c for c in ("rating", "duration") if c in df.columns])

    # Multi-country titles -> one row per country (so country filters work)
    df["country"] = df["country"].fillna("Unknown")
    df = df.assign(country=df["country"].str.split(",")).explode("country")
    df["country"] = df["country"].str.strip()

    for col in ("budget", "revenue", "popularity", "vote_count", "vote_average"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")
    df = df.dropna(subset=["release_year"]).copy()
    df["release_year"] = df["release_year"].astype(int)

    df["vote_average"] = df["vote_average"].fillna(0)
    df["popularity"] = df["popularity"].fillna(0)
    df["vote_count"] = df["vote_count"].fillna(0).astype(int)
    df["budget"] = df["budget"].fillna(0)
    df["revenue"] = df["revenue"].fillna(0)

    # ROI only where there's a *realistic* budget to divide by. TMDB-style
    # exports include ~150 titles with budget < $50K (several literally
    # budget=$1), which are placeholder/error values, not real economics —
    # dividing by them produces ROI in the hundred-thousand-percent range
    # and silently dominates every genre/language average downstream. A
    # $50K floor is the standard fix: it's well below even no-budget indie
    # filmmaking (~$100K+) so it only screens out data errors, not genuine
    # micro-budget titles.
    MIN_RELIABLE_BUDGET = 50_000
    df["has_financials"] = df["budget"] >= MIN_RELIABLE_BUDGET
    df["roi"] = np.where(df["has_financials"], (df["revenue"] - df["budget"]) / df["budget"] * 100, np.nan)
    df["profit"] = np.where(df["has_financials"], df["revenue"] - df["budget"], np.nan)
    df["profit_margin"] = np.where(df["revenue"] > 0, np.where(df["has_financials"], df["profit"] / df["revenue"] * 100, np.nan), np.nan)
    df["decade"] = (df["release_year"] // 10) * 10

    df["genres"] = df["genres"].fillna("")
    df["genre_list"] = df["genres"].str.split(",")
    df["primary_genre"] = df["genre_list"].apply(lambda g: g[0].strip() if g and g[0].strip() else "Unknown")

    df["language"] = df["language"].fillna("unknown")
    df["director"] = df["director"].fillna("Unknown")
    df["description"] = df["description"].fillna("")
    df["cast"] = df["cast"].fillna("")

    df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")

    return df.reset_index(drop=True)


def load_engagement() -> pd.DataFrame:
    """Load + clean the real Netflix engagement dataset."""
    df = pd.read_csv(ENGAGEMENT_CSV)
    df["premiere_date"] = pd.to_datetime(df["premiere_date"], errors="coerce")
    for col in ("hours_viewed_millions", "views_millions"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # A usable single "engagement score" per row even when only one of the
    # two metrics was published: views ≈ hours / typical-runtime-hours.
    # We don't fabricate a missing metric from the other (different
    # methodology, would misrepresent Netflix's own numbers) — we only
    # use whichever is present for ranking, tagged so the UI can label it.
    df["primary_metric"] = np.where(
        df["hours_viewed_millions"].notna(), "hours",
        np.where(df["views_millions"].notna(), "views", "none"),
    )
    return df


# Canonical period ordering used for any time-series chart over engagement data
ENGAGEMENT_PERIOD_ORDER = ["2023-H1", "2023-H2", "2024-H1", "2024-H2", "2025-H1", "2025-H2"]
