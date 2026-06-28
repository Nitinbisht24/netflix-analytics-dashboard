# -*- coding: utf-8 -*-
"""
core/engagement.py — Analytics over the REAL Netflix engagement dataset
(data/raw/netflix_engagement_report.csv), compiled from Netflix's official
bi-annual "What We Watched" Engagement Reports. See data/DATA_DICTIONARY.md.

Two metrics coexist in this data and are NEVER silently merged:
  - hours_viewed_millions  — total hours streamed (Netflix's own headline metric)
  - views_millions         — hours ÷ runtime (Netflix's "completed-viewing-equivalent" metric)
Each row has whichever metric Netflix/press published for it; functions
below operate on each metric independently and report which was used.
"""
from core.database import q_rows, q_one
from core.etl import ENGAGEMENT_PERIOD_ORDER


def get_engagement_kpis() -> dict:
    total = q_one("SELECT COUNT(*) AS n FROM engagement")
    # Sums exclude "All-Time" rows — those are cumulative totals that
    # already overlap with the per-half-year rows for the same titles,
    # so including both would double-count hours/views. See the same note
    # in core/database.py's engagement aggregate population.
    not_all_time = "report_period != 'All-Time'"
    hours = q_one(f"SELECT SUM(hours_viewed_millions) AS s, COUNT(*) AS n FROM engagement WHERE hours_viewed_millions IS NOT NULL AND {not_all_time}")
    views = q_one(f"SELECT SUM(views_millions) AS s, COUNT(*) AS n FROM engagement WHERE views_millions IS NOT NULL AND {not_all_time}")
    top_country = q_one("""SELECT country_origin, total_views FROM engagement_country_stats
                            ORDER BY total_views DESC LIMIT 1""")
    top_genre = q_one("""SELECT primary_genre, total_views FROM engagement_genre_stats
                          ORDER BY total_views DESC LIMIT 1""")
    movie_tv = q_rows("SELECT content_type, COUNT(*) AS n FROM engagement GROUP BY content_type")
    return {
        "total_titles": total["n"] if total else 0,
        "titles_with_hours": hours["n"] if hours else 0,
        "titles_with_views": views["n"] if views else 0,
        "sum_hours_viewed_millions": round(hours["s"] or 0, 1) if hours else 0,
        "sum_views_millions": round(views["s"] or 0, 1) if views else 0,
        "top_country_by_views": top_country["country_origin"] if top_country else None,
        "top_genre_by_views": top_genre["primary_genre"] if top_genre else None,
        "content_type_breakdown": {r["content_type"]: r["n"] for r in movie_tv},
    }


def get_engagement_top(metric: str = "views", content_type: str = None, limit: int = 15) -> dict:
    """Top titles ranked by hours_viewed_millions or views_millions."""
    col = "hours_viewed_millions" if metric == "hours" else "views_millions"
    where = f"{col} IS NOT NULL"
    params = []
    if content_type and content_type != "All":
        where += " AND content_type = ?"
        params.append(content_type)
    rows = q_rows(f"""SELECT title, content_type, primary_genre, country_origin, report_period,
                              hours_viewed_millions, views_millions
                       FROM engagement WHERE {where}
                       ORDER BY {col} DESC LIMIT ?""", (*params, limit))
    return {"metric": metric, "titles": rows}


def get_engagement_by_genre() -> dict:
    rows = q_rows("""SELECT primary_genre, title_count, total_hours, total_views, avg_hours, avg_views
                      FROM engagement_genre_stats ORDER BY total_views DESC""")
    return {
        "genres": [r["primary_genre"] for r in rows],
        "title_counts": [r["title_count"] for r in rows],
        "total_views": [round(r["total_views"] or 0, 1) for r in rows],
        "total_hours": [round(r["total_hours"] or 0, 1) for r in rows],
    }


def get_engagement_by_country() -> dict:
    rows = q_rows("""SELECT country_origin, title_count, total_hours, total_views
                      FROM engagement_country_stats ORDER BY total_views DESC LIMIT 15""")
    return {
        "countries": [r["country_origin"] for r in rows],
        "title_counts": [r["title_count"] for r in rows],
        "total_views": [round(r["total_views"] or 0, 1) for r in rows],
        "total_hours": [round(r["total_hours"] or 0, 1) for r in rows],
    }


def get_engagement_trend() -> dict:
    """Total hours/views per report period, in chronological order (All-Time excluded — it's a different window)."""
    rows = q_rows("SELECT * FROM engagement_period_trend WHERE report_period != 'All-Time'")
    by_period = {r["report_period"]: r for r in rows}
    ordered = [by_period[p] for p in ENGAGEMENT_PERIOD_ORDER if p in by_period]
    return {
        "periods": [r["report_period"] for r in ordered],
        "title_counts": [r["title_count"] for r in ordered],
        "total_hours": [round(r["total_hours"] or 0, 1) for r in ordered],
        "total_views": [round(r["total_views"] or 0, 1) for r in ordered],
        "movie_counts": [r["movie_count"] for r in ordered],
        "tv_counts": [r["tv_count"] for r in ordered],
    }


def get_engagement_insights() -> list:
    insights = []
    kpis = get_engagement_kpis()

    if kpis["top_genre_by_views"]:
        g = q_one("SELECT * FROM engagement_genre_stats WHERE primary_genre=?", (kpis["top_genre_by_views"],))
        insights.append({
            "icon": "\U0001F451", "type": "engagement", "title": "Most-Watched Genre on Netflix",
            "body": f"<b>{g['primary_genre']}</b> leads real Netflix viewership in this dataset with "
                    f"<b>{round(g['total_views'] or 0, 0):,.0f}M</b> combined views across {g['title_count']} titles "
                    f"(source: Netflix Engagement Reports).",
            "sentiment": "positive",
        })

    trend = get_engagement_trend()
    if len(trend["total_views"]) >= 2:
        delta = trend["total_views"][-1] - trend["total_views"][-2]
        pct = round(delta / trend["total_views"][-2] * 100, 1) if trend["total_views"][-2] else 0
        insights.append({
            "icon": "\U0001F4C8" if pct >= 0 else "\U0001F4C9", "type": "trend", "title": "Half-on-Half Viewing Trend",
            "body": f"Tracked views {'rose' if pct >= 0 else 'fell'} <b>{abs(pct)}%</b> from "
                    f"{trend['periods'][-2]} to {trend['periods'][-1]} across the titles in this dataset "
                    f"(note: this reflects the curated sample, not Netflix's full 18,000+ title catalogue).",
            "sentiment": "positive" if pct >= 0 else "warning",
        })

    non_us = q_one("""SELECT SUM(title_count) AS n FROM engagement_country_stats WHERE country_origin != 'United States'""")
    total_n = q_one("SELECT COUNT(*) AS n FROM engagement")
    if non_us and total_n and total_n["n"]:
        share = round((non_us["n"] or 0) / total_n["n"] * 100, 1)
        insights.append({
            "icon": "\U0001F30D", "type": "international", "title": "International Content's Share",
            "body": f"<b>{share}%</b> of titles in this real-engagement sample originate outside the United States "
                    f"\u2014 consistent with Netflix's own reporting that non-English titles regularly account for "
                    f"roughly a third of all global viewing.",
            "sentiment": "neutral",
        })

    movie_tv = kpis["content_type_breakdown"]
    if movie_tv:
        tv = movie_tv.get("TV Show", 0)
        mv = movie_tv.get("Movie", 0)
        if tv and mv:
            insights.append({
                "icon": "\U0001F4FA", "type": "mix", "title": "TV vs. Movie Mix",
                "body": f"TV shows make up <b>{round(tv / (tv + mv) * 100, 0):.0f}%</b> of the most-watched titles "
                        f"tracked here, vs. <b>{round(mv / (tv + mv) * 100, 0):.0f}%</b> for movies \u2014 multi-season "
                        f"series tend to accumulate hours long after their premiere.",
                "sentiment": "neutral",
            })

    return insights
