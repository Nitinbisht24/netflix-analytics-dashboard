# -*- coding: utf-8 -*-
"""api/recommend.py — Content-based "titles like this" recommender endpoint."""
from flask import Blueprint, jsonify, request

from core import recommender as rec

bp = Blueprint("recommend", __name__, url_prefix="/api/recommend")


@bp.route("")
def recommend():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"error": "Provide a ?title= query parameter."}), 400
    n = request.args.get("n", 8, type=int)
    return jsonify(rec.recommend(title, n=min(max(n, 1), 20)))


@bp.route("/seed-titles")
def seed_titles():
    n = request.args.get("n", 6, type=int)
    return jsonify({"titles": rec.random_seed_titles(n)})
