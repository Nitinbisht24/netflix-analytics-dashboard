# -*- coding: utf-8 -*-
"""api/market.py — REST endpoints over the movie-market dataset."""
from flask import Blueprint, jsonify, request

from core import analytics as an
from core.cache import cached

bp = Blueprint("market", __name__, url_prefix="/api")


@bp.route("/countries")
@cached
def countries():
    rows = an.get_country_comparison()
    return jsonify(sorted(rows["countries"]))


@bp.route("/kpis")
@cached
def kpis():
    return jsonify(an.get_kpis(request.args.get("country", "All")))


@bp.route("/growth")
@cached
def growth():
    return jsonify(an.get_growth(request.args.get("country", "All")))


@bp.route("/genres")
@cached
def genres():
    return jsonify(an.get_genres(request.args.get("country", "All")))


@bp.route("/roi-by-genre")
@cached
def roi_by_genre():
    return jsonify(an.get_roi_by_genre(request.args.get("country", "All")))


@bp.route("/languages")
@cached
def languages():
    return jsonify(an.get_languages(request.args.get("country", "All")))


@bp.route("/language-roi")
@cached
def language_roi():
    return jsonify(an.get_language_roi(request.args.get("country", "All")))


@bp.route("/correlations")
@cached
def correlations():
    return jsonify(an.get_correlations(request.args.get("country", "All")))


@bp.route("/yearly-trend")
@cached
def yearly_trend():
    return jsonify(an.get_yearly_trend(request.args.get("country", "All")))


@bp.route("/budget-revenue-scatter")
@cached
def budget_revenue_scatter():
    return jsonify(an.get_budget_revenue_scatter(request.args.get("country", "All")))


@bp.route("/ratings-distribution")
@cached
def ratings_distribution():
    return jsonify(an.get_ratings_dist(request.args.get("country", "All")))


@bp.route("/country-comparison")
@cached
def country_comparison():
    return jsonify(an.get_country_comparison())


@bp.route("/genre-evolution")
@cached
def genre_evolution():
    return jsonify(an.get_genre_evolution(request.args.get("country", "All")))


@bp.route("/top-titles")
@cached
def top_titles():
    limit = request.args.get("limit", 10, type=int)
    return jsonify(an.get_top_titles(request.args.get("country", "All"), limit))


@bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"results": []})
    return jsonify(an.search_titles(q, limit=request.args.get("limit", 10, type=int)))


@bp.route("/stats/genre-roi-significance")
@cached
def genre_roi_significance():
    return jsonify(an.get_genre_roi_significance(request.args.get("country", "All")))


@bp.route("/insights")
@cached
def insights():
    return jsonify({"insights": an.get_insights(request.args.get("country", "All"))})
