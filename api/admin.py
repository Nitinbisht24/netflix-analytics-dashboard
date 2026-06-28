# -*- coding: utf-8 -*-
"""api/admin.py — Lightweight ops endpoints: health check, cache control, DB rebuild."""
from flask import Blueprint, jsonify

from core import cache, database, recommender

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.route("/health")
def health():
    return jsonify({"status": "ok"})


@bp.route("/cache/clear", methods=["POST"])
def clear_cache():
    n = cache.clear()
    return jsonify({"cleared_entries": n})


@bp.route("/cache/stats")
def cache_stats():
    return jsonify(cache.stats())


@bp.route("/db/rebuild", methods=["POST"])
def rebuild_db():
    database.build_db(force=True)
    cache.clear()
    recommender.build()
    return jsonify({"status": "rebuilt"})
