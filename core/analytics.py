# -*- coding: utf-8 -*-
"""
core/analytics.py — Movie-market analytics: ROI segmentation, correlations,
regression trendlines, genre evolution, search, and the insight engine.

All functions read from the pre-aggregated SQLite tables built by
core/database.py — nothing here touches a raw DataFrame at request time.
"""
import numpy as np
import pandas as pd
from scipy import stats as sstats

from core.database import q_rows, q_one

# ─────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────

def _country_key(country: str) -> str:
    return "__ALL__" if not country or country == "All" else country


def _fmt_roi(v):
    """Clamp ROI to ±999% for chart/display sanity (raw value still stored)."""
    if v is None:
        return None
    v = float(v)
    if np.isnan(v) or np.isinf(v):
        return None
    return round(max(-999, min(999, v)), 1)


def _rolling_avg(data: list, window: int) -> list:
    result = []
    for i in range(len(data)):
        sl = data[max(0, i - window + 1): i + 1]
        result.append(round(sum(sl) / len(sl), 1))
    return result


def _linear_regression(x: list, y: list):
    x_arr = np.array(x, dtype=float)
    y_arr = np.array(y, dtype=float)
    mask = ~(np.isnan(x_arr) | np.isnan(y_arr))
    x_arr, y_arr = x_arr[mask], y_arr[mask]
    if len(x_arr) < 3:
        return None
    coef = np.polyfit(x_arr, y_arr, 1)
    slope, intercept = coef
    y_pred = (slope * x_arr + intercept).tolist()
    r = np.corrcoef(x_arr, y_arr)[0, 1] if len(x_arr) > 1 else np.nan
    return {
        "x": x_arr.tolist(),
        "y_pred": [round(v, 2) for v in y_pred],
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 4),
        "r_squared": round(float(r ** 2), 3) if not np.isnan(r) else None,
    }


# ─────────────────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────────────────

def get_kpis(country: str) -> dict:
    ck = _country_key(country)
    where = "" if ck == "__ALL__" else "WHERE country=?"
    params = () if ck == "__ALL__" else (ck,)

    row = q_one(f"""
        SELECT COUNT(*) AS total, AVG(vote_average) AS avg_rating,
               AVG(CASE WHEN has_financials THEN budget END) AS avg_budget,
               AVG(CASE WHEN has_financials THEN revenue END) AS avg_revenue,
               SUM(CASE WHEN has_financials THEN budget END) AS sum_budget,
               SUM(CASE WHEN has_financials THEN revenue END) AS sum_revenue,
               SUM(has_financials) AS n_financials
        FROM titles {where}
    """, params)

    lang_where = "WHERE country='__ALL__'" if ck == "__ALL__" else "WHERE country=?"
    lang_row = q_one(f"SELECT language FROM language_stats {lang_where} ORDER BY count DESC LIMIT 1",
                      () if ck == "__ALL__" else (ck,))

    sb, sr = row["sum_budget"] or 0, row["sum_revenue"] or 0
    roi = round((sr - sb) / sb * 100, 1) if sb > 0 else 0

    yr_where = "country='__ALL__'" if ck == "__ALL__" else "country=?"
    years = q_rows(f"SELECT release_year, count FROM yearly_trend WHERE {yr_where} ORDER BY release_year DESC LIMIT 2",
                   () if ck == "__ALL__" else (ck,))
    yoy = None
    if len(years) == 2:
        cur, prev = years[0]["count"], years[1]["count"]
        yoy = round((cur - prev) / prev * 100, 1) if prev else None

    return {
        "total": row["total"] or 0,
        "avg_rating": round(row["avg_rating"] or 0, 2),
        "avg_budget": int(row["avg_budget"] or 0),
        "avg_revenue": int(row["avg_revenue"] or 0),
        "total_budget": int(sb),
        "total_revenue": int(sr),
        "roi": roi,
        "top_language": lang_row["language"] if lang_row else "\u2014",
        "yoy_growth": yoy,
        "n_with_financials": row["n_financials"] or 0,
        "pct_with_financials": round((row["n_financials"] or 0) / row["total"] * 100, 1) if row["total"] else 0,
    }


# ─────────────────────────────────────────────────────────────────────────
# Growth trend
# ─────────────────────────────────────────────────────────────────────────

def get_growth(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("SELECT release_year, count, avg_rating, avg_roi FROM yearly_trend WHERE country=? ORDER BY release_year", (ck,))
    counts = [r["count"] for r in rows]
    return {
        "years": [r["release_year"] for r in rows],
        "counts": counts,
        "rolling": _rolling_avg(counts, 3),
        "avg_ratings": [round(r["avg_rating"] or 0, 2) for r in rows],
    }


# ─────────────────────────────────────────────────────────────────────────
# Genre analytics
# ─────────────────────────────────────────────────────────────────────────

def get_genres(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("""SELECT genre, count, avg_roi, avg_rating, avg_budget, avg_revenue
                      FROM genre_stats WHERE country=? ORDER BY count DESC LIMIT 10""", (ck,))
    return {
        "genres": [r["genre"] for r in rows],
        "counts": [r["count"] for r in rows],
        "avg_roi": [_fmt_roi(r["avg_roi"]) for r in rows],
        "avg_ratings": [round(r["avg_rating"] or 0, 2) for r in rows],
        "avg_budgets": [round((r["avg_budget"] or 0) / 1e6, 1) for r in rows],
        "avg_revenues": [round((r["avg_revenue"] or 0) / 1e6, 1) for r in rows],
    }


def get_roi_by_genre(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("""SELECT genre, avg_roi, count, avg_rating, avg_budget, avg_revenue
                      FROM genre_stats WHERE country=? AND count >= 10
                      ORDER BY avg_roi DESC LIMIT 12""", (ck,))
    return {
        "genres": [r["genre"] for r in rows],
        "roi": [_fmt_roi(r["avg_roi"]) for r in rows],
        "counts": [r["count"] for r in rows],
        "ratings": [round(r["avg_rating"] or 0, 2) for r in rows],
        "budgets": [round((r["avg_budget"] or 0) / 1e6, 1) for r in rows],
        "revenues": [round((r["avg_revenue"] or 0) / 1e6, 1) for r in rows],
    }


# ─────────────────────────────────────────────────────────────────────────
# Language analytics
# ─────────────────────────────────────────────────────────────────────────

def get_languages(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("""SELECT language, count, avg_roi, avg_rating FROM language_stats
                      WHERE country=? ORDER BY count DESC LIMIT 8""", (ck,))
    return {
        "languages": [r["language"] for r in rows],
        "counts": [r["count"] for r in rows],
        "avg_roi": [_fmt_roi(r["avg_roi"]) for r in rows],
        "avg_ratings": [round(r["avg_rating"] or 0, 2) for r in rows],
    }


def get_language_roi(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("""SELECT language, avg_roi, count, avg_rating FROM language_stats
                      WHERE country=? AND count >= 20 ORDER BY avg_roi DESC LIMIT 10""", (ck,))
    return {
        "languages": [r["language"] for r in rows],
        "roi": [_fmt_roi(r["avg_roi"]) for r in rows],
        "counts": [r["count"] for r in rows],
        "ratings": [round(r["avg_rating"] or 0, 2) for r in rows],
    }


# ─────────────────────────────────────────────────────────────────────────
# Correlations
# ─────────────────────────────────────────────────────────────────────────

CORR_VARS = ["budget", "revenue", "vote_average", "popularity", "vote_count"]
CORR_LABELS = {"budget": "Budget", "revenue": "Revenue", "vote_average": "Rating",
               "popularity": "Popularity", "vote_count": "Vote Count"}


def get_correlations(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("SELECT var1, var2, pearson FROM correlations WHERE country=?", (ck,))
    n = len(CORR_VARS)
    mat = [[None] * n for _ in range(n)]
    for i in range(n):
        mat[i][i] = 1.0
    idx = {v: i for i, v in enumerate(CORR_VARS)}
    for r in rows:
        i, j = idx[r["var1"]], idx[r["var2"]]
        mat[i][j] = r["pearson"]
        mat[j][i] = r["pearson"]
    return {"labels": [CORR_LABELS[v] for v in CORR_VARS], "matrix": mat}


# ─────────────────────────────────────────────────────────────────────────
# Yearly budget vs revenue (regression)
# ─────────────────────────────────────────────────────────────────────────

def get_yearly_trend(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("""SELECT release_year, count, avg_budget, avg_revenue, avg_roi, avg_rating
                      FROM yearly_trend WHERE country=? ORDER BY release_year""", (ck,))
    budgets = [round((r["avg_budget"] or 0) / 1e6, 2) for r in rows]
    revenues = [round((r["avg_revenue"] or 0) / 1e6, 2) for r in rows]
    years = [r["release_year"] for r in rows]
    reg = _linear_regression(years, revenues)
    return {
        "years": years, "avg_budgets": budgets, "avg_revenues": revenues,
        "avg_roi": [_fmt_roi(r["avg_roi"]) for r in rows],
        "avg_rating": [round(r["avg_rating"] or 0, 2) for r in rows],
        "regression": reg,
    }


# ─────────────────────────────────────────────────────────────────────────
# Budget vs Revenue scatter (stratified sample)
# ─────────────────────────────────────────────────────────────────────────

def get_budget_revenue_scatter(country: str, n: int = 400) -> dict:
    ck = _country_key(country)
    where = "budget > 0 AND revenue > 0" + ("" if ck == "__ALL__" else " AND country=?")
    params = () if ck == "__ALL__" else (ck,)
    all_rows = q_rows(f"""SELECT DISTINCT title, budget, revenue, vote_average, release_year, language
                          FROM titles WHERE {where}""", params)
    if not all_rows:
        return {"titles": [], "budgets": [], "revenues": [], "ratings": [], "profitable": []}

    df = pd.DataFrame(all_rows)
    df["decade"] = (df["release_year"] // 5) * 5
    sampled = (
        df.groupby("decade", group_keys=False)
        .apply(lambda x: x.sample(min(len(x), max(1, n // df["decade"].nunique())), random_state=42))
        .reset_index(drop=True)
    )

    x = sampled["budget"].values / 1e6
    y = sampled["revenue"].values / 1e6
    reg = _linear_regression(x.tolist(), y.tolist())

    return {
        "titles": sampled["title"].tolist(),
        "budgets": (sampled["budget"] / 1e6).round(1).tolist(),
        "revenues": (sampled["revenue"] / 1e6).round(1).tolist(),
        "ratings": sampled["vote_average"].round(2).tolist(),
        "profitable": (sampled["revenue"] > sampled["budget"]).tolist(),
        "languages": sampled["language"].tolist(),
        "regression": reg,
        "r_squared": round(float(np.corrcoef(x, y)[0, 1] ** 2), 3) if len(x) > 2 else None,
    }


# ─────────────────────────────────────────────────────────────────────────
# Ratings distribution
# ─────────────────────────────────────────────────────────────────────────

def get_ratings_dist(country: str) -> dict:
    ck = _country_key(country)
    where = "vote_average > 0" + ("" if ck == "__ALL__" else " AND country=?")
    params = () if ck == "__ALL__" else (ck,)
    rows = q_rows(f"SELECT vote_average FROM titles WHERE {where}", params)
    vals = pd.Series([r["vote_average"] for r in rows])
    bins = [0, 2, 4, 5, 6, 7, 8, 9, 10]
    labels = ["0-2", "2-4", "4-5", "5-6", "6-7", "7-8", "8-9", "9-10"]
    cut = pd.cut(vals, bins=bins, labels=labels, right=True, include_lowest=True)
    freq = cut.value_counts().reindex(labels, fill_value=0)
    return {"bins": labels, "counts": [int(v) for v in freq.tolist()]}


# ─────────────────────────────────────────────────────────────────────────
# Country comparison
# ─────────────────────────────────────────────────────────────────────────

def get_country_comparison() -> dict:
    rows = q_rows("""SELECT country, count, avg_roi, avg_rating, avg_budget, avg_revenue
                      FROM country_stats ORDER BY count DESC LIMIT 15""")
    return {
        "countries": [r["country"] for r in rows],
        "counts": [r["count"] for r in rows],
        "avg_roi": [_fmt_roi(r["avg_roi"]) for r in rows],
        "avg_ratings": [round(r["avg_rating"] or 0, 2) for r in rows],
        "avg_budgets": [round((r["avg_budget"] or 0) / 1e6, 1) for r in rows],
        "avg_revenues": [round((r["avg_revenue"] or 0) / 1e6, 1) for r in rows],
    }


# ─────────────────────────────────────────────────────────────────────────
# Genre evolution heatmap
# ─────────────────────────────────────────────────────────────────────────

def get_genre_evolution(country: str) -> dict:
    ck = _country_key(country)
    rows = q_rows("""SELECT period, genre, count, share FROM genre_evolution
                      WHERE country=? ORDER BY period, share DESC""", (ck,))
    if not rows:
        return {"periods": [], "genres": [], "matrix": []}
    periods = sorted({r["period"] for r in rows})
    genres, seen = [], set()
    for r in rows:
        if r["genre"] not in seen:
            genres.append(r["genre"])
            seen.add(r["genre"])
    lookup = {(r["period"], r["genre"]): r["share"] for r in rows}
    matrix = [[lookup.get((p, g), 0) for p in periods] for g in genres]
    return {"periods": periods, "genres": genres, "matrix": matrix}


# ─────────────────────────────────────────────────────────────────────────
# Top titles & search
# ─────────────────────────────────────────────────────────────────────────

def get_top_titles(country: str, limit: int = 10) -> dict:
    ck = _country_key(country)
    where = "" if ck == "__ALL__" else "WHERE country=?"
    params = () if ck == "__ALL__" else (ck,)
    rows = q_rows(f"""SELECT DISTINCT title, release_year, vote_average, popularity, budget, revenue,
                             roi, genres, language FROM titles {where}
                      ORDER BY popularity DESC LIMIT {int(limit)}""", params)
    out = []
    for r in rows:
        d = dict(r)
        d["budget"] = round((d["budget"] or 0) / 1e6, 1)
        d["revenue"] = round((d["revenue"] or 0) / 1e6, 1)
        d["roi"] = _fmt_roi(d["roi"])
        d["vote_average"] = round(d["vote_average"] or 0, 1)
        d["popularity"] = round(d["popularity"] or 0, 1)
        out.append(d)
    return {"titles": out}


def search_titles(query: str, limit: int = 10) -> dict:
    """Lightweight title search used by the global search box."""
    q = f"%{query.strip()}%"
    rows = q_rows("""SELECT DISTINCT title, release_year, vote_average, genres, language
                      FROM titles WHERE title LIKE ? ORDER BY vote_average DESC LIMIT ?""",
                  (q, limit))
    return {"results": rows}


# ─────────────────────────────────────────────────────────────────────────
# Statistical significance — is genre ROI variation real or noise?
# ─────────────────────────────────────────────────────────────────────────

def get_genre_roi_significance(country: str, top_n: int = 6) -> dict:
    """One-way ANOVA across the top-N genres' raw per-title ROI values —
    answers "is the ROI gap between genres statistically significant, or
    could it just be sampling noise?" using scipy.stats."""
    ck = _country_key(country)
    top = q_rows("""SELECT genre FROM genre_stats WHERE country=? AND count>=15
                     ORDER BY count DESC LIMIT ?""", (ck, top_n))
    genre_names = [r["genre"] for r in top]
    if len(genre_names) < 2:
        return {"genres": genre_names, "f_stat": None, "p_value": None, "significant": None}

    samples = []
    for g in genre_names:
        like = f"%{g}%"
        where = "genres LIKE ? AND roi IS NOT NULL" + ("" if ck == "__ALL__" else " AND country=?")
        params = (like,) if ck == "__ALL__" else (like, ck)
        vals = q_rows(f"SELECT roi FROM titles WHERE {where}", params)
        arr = np.array([v["roi"] for v in vals if v["roi"] is not None])
        arr = np.clip(arr, -999, 999)  # same display-sanity clamp as everywhere else
        if len(arr) >= 5:
            samples.append(arr)

    if len(samples) < 2:
        return {"genres": genre_names, "f_stat": None, "p_value": None, "significant": None}

    f_stat, p_value = sstats.f_oneway(*samples)
    return {
        "genres": genre_names,
        "f_stat": round(float(f_stat), 2),
        "p_value": round(float(p_value), 5),
        "significant": bool(p_value < 0.05),
        "n_genres_tested": len(samples),
    }


# ─────────────────────────────────────────────────────────────────────────
# Insight engine
# ─────────────────────────────────────────────────────────────────────────

def get_insights(country: str) -> list:
    ck = _country_key(country)
    lbl = "Globally" if ck == "__ALL__" else f"In {country}"
    insights = []

    top_roi = q_one("""SELECT genre, avg_roi, count FROM genre_stats
                        WHERE country=? AND count >= 15 ORDER BY avg_roi DESC LIMIT 1""", (ck,))
    if top_roi and top_roi["avg_roi"]:
        insights.append({
            "icon": "\U0001F4B0", "type": "roi", "title": "Highest-ROI Genre",
            "body": f"{lbl}, <b>{top_roi['genre']}</b> delivers the best returns with an average ROI of "
                    f"<b>{_fmt_roi(top_roi['avg_roi'])}%</b> across {top_roi['count']} titles.",
            "sentiment": "positive",
        })

    corr = q_one("SELECT pearson FROM correlations WHERE country=? AND var1='budget' AND var2='revenue'", (ck,))
    if corr and corr["pearson"] is not None:
        r = corr["pearson"]
        strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.4 else "weak"
        insights.append({
            "icon": "\U0001F4CA", "type": "correlation", "title": "Budget \u2194 Revenue Correlation",
            "body": f"{lbl} there is a <b>{strength}</b> positive correlation (r = {r:.2f}) between production "
                    f"budget and box-office revenue, suggesting "
                    f"{'spending more generally pays off.' if abs(r) > 0.5 else 'budget alone does not guarantee success.'}",
            "sentiment": "neutral",
        })

    recent = q_rows("SELECT release_year, count FROM yearly_trend WHERE country=? ORDER BY release_year DESC LIMIT 3", (ck,))
    if len(recent) >= 2:
        delta = recent[0]["count"] - recent[1]["count"]
        pct = round(delta / recent[1]["count"] * 100, 1) if recent[1]["count"] else 0
        arrow = "grew" if pct > 0 else "declined"
        insights.append({
            "icon": "\U0001F4C8" if pct > 0 else "\U0001F4C9", "type": "growth", "title": "Content Volume Trend",
            "body": f"Content production <b>{arrow} by {abs(pct)}%</b> from {recent[1]['release_year']} "
                    f"({recent[1]['count']} titles) to {recent[0]['release_year']} ({recent[0]['count']} titles).",
            "sentiment": "positive" if pct > 0 else "warning",
        })

    top_lang = q_one("SELECT language, count FROM language_stats WHERE country=? ORDER BY count DESC LIMIT 1", (ck,))
    total = q_one("SELECT COUNT(*) AS n FROM titles" + (" WHERE country=?" if ck != "__ALL__" else ""),
                  (ck,) if ck != "__ALL__" else ())
    if top_lang and total and total["n"]:
        share = round(top_lang["count"] / total["n"] * 100, 1)
        insights.append({
            "icon": "\U0001F5E3\uFE0F", "type": "language", "title": "Language Dominance",
            "body": f"{lbl}, <b>{top_lang['language'].upper()}</b>-language content accounts for "
                    f"<b>{share}%</b> of all titles, reflecting the "
                    f"{'global' if ck == '__ALL__' else 'regional'} market composition.",
            "sentiment": "neutral",
        })

    top_rated = q_one("SELECT genre, avg_rating, count FROM genre_stats WHERE country=? AND count >= 20 ORDER BY avg_rating DESC LIMIT 1", (ck,))
    if top_rated:
        insights.append({
            "icon": "\u2B50", "type": "rating", "title": "Audience Favourite Genre",
            "body": f"<b>{top_rated['genre']}</b> earns the highest audience rating "
                    f"(<b>{round(top_rated['avg_rating'], 2)}/10</b>) across {top_rated['count']} titles {lbl.lower()}.",
            "sentiment": "positive",
        })

    worst_roi = q_one("SELECT genre, avg_roi, count FROM genre_stats WHERE country=? AND count >= 15 ORDER BY avg_roi ASC LIMIT 1", (ck,))
    if worst_roi and worst_roi["avg_roi"] is not None and worst_roi["avg_roi"] < 0:
        insights.append({
            "icon": "\u26A0\uFE0F", "type": "warning", "title": "Underperforming Segment",
            "body": f"<b>{worst_roi['genre']}</b> shows a negative ROI of <b>{_fmt_roi(worst_roi['avg_roi'])}%</b> "
                    f"across {worst_roi['count']} titles \u2014 a segment to approach with caution.",
            "sentiment": "negative",
        })

    pr_corr = q_one("SELECT pearson FROM correlations WHERE country=? AND var1='vote_average' AND var2='popularity'", (ck,))
    if pr_corr and pr_corr["pearson"] is not None:
        r = pr_corr["pearson"]
        if abs(r) < 0.2:
            insights.append({
                "icon": "\U0001F50D", "type": "insight", "title": "Popularity \u2260 Quality",
                "body": f"The near-zero correlation (r = {r:.2f}) between audience rating and popularity score "
                        f"suggests that viral hits {lbl.lower()} are <b>not necessarily the highest-rated content</b>.",
                "sentiment": "neutral",
            })

    sig = get_genre_roi_significance(country)
    if sig.get("p_value") is not None:
        verdict = "statistically significant" if sig["significant"] else "not statistically significant at the 5% level"
        p_disp = "< 0.001" if sig["p_value"] < 0.001 else f"= {sig['p_value']}"
        insights.append({
            "icon": "\U0001F9EA", "type": "stats", "title": "Is the Genre ROI Gap Real?",
            "body": f"A one-way ANOVA across the top {sig['n_genres_tested']} genres by ROI "
                    f"(F = {sig['f_stat']}, p {p_disp}) finds the gap is "
                    f"<b>{verdict}</b> \u2014 {'genre really does drive ROI' if sig['significant'] else 'observed differences could be due to chance / outliers'}.",
            "sentiment": "neutral",
        })

    return insights[:8]
