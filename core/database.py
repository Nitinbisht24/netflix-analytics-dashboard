# -*- coding: utf-8 -*-
"""
core/database.py — SQLite layer.

Builds a set of pre-aggregated tables from the cleaned ETL DataFrames so
every API request hits an indexed SQL query instead of re-crunching a
22k-row DataFrame on every call. Idempotent: build_db() skips rebuilding
if data/processed/analytics.db already exists, unless force=True.
"""
import logging
import os
import sqlite3

import numpy as np
import pandas as pd

from core import etl

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_HERE, "data", "processed", "analytics.db")


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def build_db(force: bool = False) -> None:
    if os.path.exists(DB_PATH) and not force:
        logger.info("DB already exists at %s — skipping rebuild.", DB_PATH)
        return

    logger.info("Building SQLite DB from raw CSVs …")
    movies = etl.load_movie_market()
    engagement = etl.load_engagement()

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    with get_conn() as conn:
        _create_schema(conn)
        _populate_titles(conn, movies)
        _populate_genre_stats(conn, movies)
        _populate_language_stats(conn, movies)
        _populate_yearly_trend(conn, movies)
        _populate_country_stats(conn, movies)
        _populate_correlations(conn, movies)
        _populate_genre_evolution(conn, movies)
        _populate_engagement(conn, engagement)
        _populate_engagement_genre_stats(conn, engagement)
        _populate_engagement_country_stats(conn, engagement)
        _populate_engagement_period_trend(conn, engagement)
        conn.execute("ANALYZE")

    logger.info("DB build complete: %s", DB_PATH)


# ─────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────

def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    DROP TABLE IF EXISTS titles;
    DROP TABLE IF EXISTS genre_stats;
    DROP TABLE IF EXISTS language_stats;
    DROP TABLE IF EXISTS yearly_trend;
    DROP TABLE IF EXISTS country_stats;
    DROP TABLE IF EXISTS correlations;
    DROP TABLE IF EXISTS genre_evolution;
    DROP TABLE IF EXISTS engagement;
    DROP TABLE IF EXISTS engagement_genre_stats;
    DROP TABLE IF EXISTS engagement_country_stats;
    DROP TABLE IF EXISTS engagement_period_trend;

    CREATE TABLE titles (
        show_id       INTEGER,
        title         TEXT,
        country       TEXT,
        release_year  INTEGER,
        genres        TEXT,
        primary_genre TEXT,
        language      TEXT,
        director      TEXT,
        budget        REAL,
        revenue       REAL,
        roi           REAL,
        profit_margin REAL,
        popularity    REAL,
        vote_average  REAL,
        vote_count    INTEGER,
        has_financials INTEGER
    );
    CREATE INDEX idx_titles_country ON titles(country);
    CREATE INDEX idx_titles_year    ON titles(release_year);
    CREATE INDEX idx_titles_title   ON titles(title);

    CREATE TABLE genre_stats (
        country     TEXT,
        genre       TEXT,
        count       INTEGER,
        avg_roi     REAL,
        avg_rating  REAL,
        avg_budget  REAL,
        avg_revenue REAL,
        total_revenue REAL
    );
    CREATE INDEX idx_genre_country ON genre_stats(country);

    CREATE TABLE language_stats (
        country     TEXT,
        language    TEXT,
        count       INTEGER,
        avg_roi     REAL,
        avg_rating  REAL
    );
    CREATE INDEX idx_lang_country ON language_stats(country);

    CREATE TABLE yearly_trend (
        country       TEXT,
        release_year  INTEGER,
        count         INTEGER,
        avg_budget    REAL,
        avg_revenue   REAL,
        avg_roi       REAL,
        avg_rating    REAL,
        total_revenue REAL
    );
    CREATE INDEX idx_year_country ON yearly_trend(country);

    CREATE TABLE country_stats (
        country      TEXT PRIMARY KEY,
        count        INTEGER,
        avg_roi      REAL,
        avg_rating   REAL,
        avg_budget   REAL,
        avg_revenue  REAL,
        top_genre    TEXT,
        top_language TEXT
    );

    CREATE TABLE correlations (
        country TEXT,
        var1    TEXT,
        var2    TEXT,
        pearson REAL
    );
    CREATE INDEX idx_corr_country ON correlations(country);

    CREATE TABLE genre_evolution (
        country      TEXT,
        period       TEXT,
        genre        TEXT,
        count        INTEGER,
        share        REAL
    );
    CREATE INDEX idx_evo_country ON genre_evolution(country);

    CREATE TABLE engagement (
        title          TEXT,
        content_type   TEXT,
        primary_genre  TEXT,
        genre_detail   TEXT,
        country_origin TEXT,
        language       TEXT,
        report_period  TEXT,
        premiere_date  TEXT,
        hours_viewed_millions REAL,
        views_millions REAL,
        primary_metric TEXT,
        source         TEXT
    );
    CREATE INDEX idx_eng_period ON engagement(report_period);
    CREATE INDEX idx_eng_genre  ON engagement(primary_genre);
    CREATE INDEX idx_eng_country ON engagement(country_origin);

    CREATE TABLE engagement_genre_stats (
        primary_genre TEXT,
        title_count   INTEGER,
        total_hours   REAL,
        total_views   REAL,
        avg_hours     REAL,
        avg_views     REAL
    );

    CREATE TABLE engagement_country_stats (
        country_origin TEXT,
        title_count    INTEGER,
        total_hours    REAL,
        total_views    REAL
    );

    CREATE TABLE engagement_period_trend (
        report_period TEXT,
        title_count   INTEGER,
        total_hours   REAL,
        total_views   REAL,
        movie_count   INTEGER,
        tv_count      INTEGER
    );
    """)


# ─────────────────────────────────────────────────────────────────────────
# Movie-market population (largely the same shape as the original project,
# extended with primary_genre / profit_margin / has_financials)
# ─────────────────────────────────────────────────────────────────────────

def _populate_titles(conn, df: pd.DataFrame) -> None:
    cols = ["show_id", "title", "country", "release_year", "genres", "primary_genre",
            "language", "director", "budget", "revenue", "roi", "profit_margin",
            "popularity", "vote_average", "vote_count", "has_financials"]
    out = df[cols].copy()
    out["has_financials"] = out["has_financials"].astype(int)
    rows = out.where(pd.notnull(out), None).values.tolist()
    conn.executemany(f"INSERT INTO titles VALUES ({','.join(['?'] * len(cols))})", rows)


def _populate_genre_stats(conn, df: pd.DataFrame) -> None:
    exploded = df.explode("genre_list").copy()
    exploded["genre_list"] = exploded["genre_list"].str.strip()
    exploded = exploded[exploded["genre_list"] != ""]

    rows = []
    for country_val in ["__ALL__"] + df["country"].unique().tolist():
        sub = exploded if country_val == "__ALL__" else exploded[exploded["country"] == country_val]
        if len(sub) == 0:
            continue
        grp = sub.groupby("genre_list").agg(
            count=("title", "count"),
            avg_roi=("roi", "mean"),
            avg_rating=("vote_average", "mean"),
            avg_budget=("budget", "mean"),
            avg_revenue=("revenue", "mean"),
            total_revenue=("revenue", "sum"),
        ).reset_index()
        grp = grp[grp["count"] >= 5]
        for _, r in grp.iterrows():
            rows.append((
                country_val, r["genre_list"], int(r["count"]),
                _safe(r["avg_roi"]), _safe(r["avg_rating"]),
                _safe(r["avg_budget"]), _safe(r["avg_revenue"]), _safe(r["total_revenue"]),
            ))
    conn.executemany("INSERT INTO genre_stats VALUES (?,?,?,?,?,?,?,?)", rows)


def _populate_language_stats(conn, df: pd.DataFrame) -> None:
    rows = []
    for country_val in ["__ALL__"] + df["country"].unique().tolist():
        sub = df if country_val == "__ALL__" else df[df["country"] == country_val]
        if len(sub) == 0:
            continue
        grp = sub.groupby("language").agg(
            count=("title", "count"), avg_roi=("roi", "mean"), avg_rating=("vote_average", "mean"),
        ).reset_index()
        for _, r in grp.iterrows():
            rows.append((country_val, r["language"], int(r["count"]), _safe(r["avg_roi"]), _safe(r["avg_rating"])))
    conn.executemany("INSERT INTO language_stats VALUES (?,?,?,?,?)", rows)


def _populate_yearly_trend(conn, df: pd.DataFrame) -> None:
    rows = []
    for country_val in ["__ALL__"] + df["country"].unique().tolist():
        sub = df if country_val == "__ALL__" else df[df["country"] == country_val]
        if len(sub) == 0:
            continue
        grp = sub.groupby("release_year").agg(
            count=("title", "count"), avg_budget=("budget", "mean"), avg_revenue=("revenue", "mean"),
            avg_roi=("roi", "mean"), avg_rating=("vote_average", "mean"), total_revenue=("revenue", "sum"),
        ).reset_index().sort_values("release_year")
        for _, r in grp.iterrows():
            rows.append((
                country_val, int(r["release_year"]), int(r["count"]),
                _safe(r["avg_budget"]), _safe(r["avg_revenue"]),
                _safe(r["avg_roi"]), _safe(r["avg_rating"]), _safe(r["total_revenue"]),
            ))
    conn.executemany("INSERT INTO yearly_trend VALUES (?,?,?,?,?,?,?,?)", rows)


def _populate_country_stats(conn, df: pd.DataFrame) -> None:
    exploded_g = df.explode("genre_list").copy()
    exploded_g["genre_list"] = exploded_g["genre_list"].str.strip()

    rows = []
    for country_val in df["country"].unique().tolist():
        sub = df[df["country"] == country_val]
        if len(sub) < 5:
            continue
        sub_g = exploded_g[exploded_g["country"] == country_val]
        top_genre = sub_g["genre_list"].value_counts().idxmax() if len(sub_g) else None
        top_language = sub["language"].value_counts().idxmax() if len(sub) else None
        rows.append((
            country_val, int(len(sub)), _safe(sub["roi"].mean()), _safe(sub["vote_average"].mean()),
            _safe(sub["budget"].mean()), _safe(sub["revenue"].mean()), top_genre, top_language,
        ))
    conn.executemany("INSERT OR REPLACE INTO country_stats VALUES (?,?,?,?,?,?,?,?)", rows)


def _populate_correlations(conn, df: pd.DataFrame) -> None:
    num_cols = ["budget", "revenue", "vote_average", "popularity", "vote_count"]
    rows = []
    for country_val in ["__ALL__"] + df["country"].unique().tolist():
        sub = df if country_val == "__ALL__" else df[df["country"] == country_val]
        if len(sub) < 30:
            continue
        corr = sub[num_cols].corr()
        for i, v1 in enumerate(num_cols):
            for j, v2 in enumerate(num_cols):
                if j > i:
                    val = corr.loc[v1, v2]
                    rows.append((country_val, v1, v2, None if pd.isna(val) else round(float(val), 4)))
    conn.executemany("INSERT INTO correlations VALUES (?,?,?,?)", rows)


def _populate_genre_evolution(conn, df: pd.DataFrame) -> None:
    exploded = df.explode("genre_list").copy()
    exploded["genre_list"] = exploded["genre_list"].str.strip()
    exploded = exploded[exploded["genre_list"] != ""]

    bins = [2009, 2014, 2017, 2020, 2023, 2026]
    labels = ["2010-14", "2015-17", "2018-20", "2021-23", "2024+"]
    exploded["period"] = pd.cut(exploded["release_year"], bins=bins, labels=labels, right=True).astype(str)

    top_genres = exploded["genre_list"].value_counts().head(8).index.tolist()
    exploded = exploded[exploded["genre_list"].isin(top_genres)]

    rows = []
    for country_val in ["__ALL__"] + df["country"].unique().tolist():
        sub = exploded if country_val == "__ALL__" else exploded[exploded["country"] == country_val]
        if len(sub) < 20:
            continue
        grp = sub.groupby(["period", "genre_list"]).size().reset_index(name="count")
        period_totals = grp.groupby("period")["count"].transform("sum")
        grp["share"] = (grp["count"] / period_totals * 100).round(2)
        for _, r in grp.iterrows():
            rows.append((country_val, r["period"], r["genre_list"], int(r["count"]), float(r["share"])))
    conn.executemany("INSERT INTO genre_evolution VALUES (?,?,?,?,?)", rows)


# ─────────────────────────────────────────────────────────────────────────
# Engagement population (NEW — real Netflix engagement-report data)
# ─────────────────────────────────────────────────────────────────────────

def _populate_engagement(conn, df: pd.DataFrame) -> None:
    cols = ["title", "content_type", "primary_genre", "genre_detail", "country_origin",
            "language", "report_period", "premiere_date", "hours_viewed_millions",
            "views_millions", "primary_metric", "source"]
    out = df[cols].copy()
    out["premiere_date"] = out["premiere_date"].dt.strftime("%Y-%m-%d")
    rows = out.where(pd.notnull(out), None).values.tolist()
    conn.executemany(f"INSERT INTO engagement VALUES ({','.join(['?'] * len(cols))})", rows)


def _populate_engagement_genre_stats(conn, df: pd.DataFrame) -> None:
    # "All-Time" rows are cumulative totals that already overlap with the
    # per-half-year rows for the same titles (e.g. Squid Game S2 appears
    # both as an All-Time leader and inside 2024-H2) — summing both would
    # double-count hours/views. Sums here are scoped to the six dated
    # half-year reports only; get_engagement_top() still surfaces All-Time
    # leaders individually, where ranking (not summing) makes that safe.
    period_only = df[df["report_period"] != "All-Time"]
    grp = period_only.groupby("primary_genre").agg(
        title_count=("title", "count"),
        total_hours=("hours_viewed_millions", "sum"),
        total_views=("views_millions", "sum"),
        avg_hours=("hours_viewed_millions", "mean"),
        avg_views=("views_millions", "mean"),
    ).reset_index()
    rows = [(r["primary_genre"], int(r["title_count"]), _safe(r["total_hours"]), _safe(r["total_views"]),
             _safe(r["avg_hours"]), _safe(r["avg_views"])) for _, r in grp.iterrows()]
    conn.executemany("INSERT INTO engagement_genre_stats VALUES (?,?,?,?,?,?)", rows)


def _populate_engagement_country_stats(conn, df: pd.DataFrame) -> None:
    period_only = df[df["report_period"] != "All-Time"]  # see note above
    grp = period_only.groupby("country_origin").agg(
        title_count=("title", "count"),
        total_hours=("hours_viewed_millions", "sum"),
        total_views=("views_millions", "sum"),
    ).reset_index()
    rows = [(r["country_origin"], int(r["title_count"]), _safe(r["total_hours"]), _safe(r["total_views"]))
            for _, r in grp.iterrows()]
    conn.executemany("INSERT INTO engagement_country_stats VALUES (?,?,?,?)", rows)


def _populate_engagement_period_trend(conn, df: pd.DataFrame) -> None:
    rows = []
    for period in df["report_period"].unique().tolist():
        sub = df[df["report_period"] == period]
        rows.append((
            period, int(len(sub)),
            _safe(sub["hours_viewed_millions"].sum()), _safe(sub["views_millions"].sum()),
            int((sub["content_type"] == "Movie").sum()), int((sub["content_type"] == "TV Show").sum()),
        ))
    conn.executemany("INSERT INTO engagement_period_trend VALUES (?,?,?,?,?,?)", rows)


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _safe(v):
    if v is None:
        return None
    try:
        if np.isnan(v) or np.isinf(v):
            return None
    except (TypeError, ValueError):
        pass
    return float(v)


def q_rows(sql: str, params: tuple = ()) -> list:
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def q_one(sql: str, params: tuple = ()):
    rows = q_rows(sql, params)
    return rows[0] if rows else None
