# -*- coding: utf-8 -*-
"""api/engagement.py — REST endpoints over the real Netflix engagement-report dataset."""
from flask import Blueprint, jsonify, request

from core import engagement as eng
from core.cache import cached

bp = Blueprint("engagement", __name__, url_prefix="/api/engagement")


@bp.route("/kpis")
@cached
def kpis():
    return jsonify(eng.get_engagement_kpis())


@bp.route("/top")
@cached
def top():
    metric = request.args.get("metric", "views")
    content_type = request.args.get("content_type", "All")
    limit = request.args.get("limit", 15, type=int)
    return jsonify(eng.get_engagement_top(metric, content_type, limit))


@bp.route("/by-genre")
@cached
def by_genre():
    return jsonify(eng.get_engagement_by_genre())


@bp.route("/by-country")
@cached
def by_country():
    return jsonify(eng.get_engagement_by_country())


@bp.route("/trend")
@cached
def trend():
    return jsonify(eng.get_engagement_trend())


@bp.route("/insights")
@cached
def insights():
    return jsonify({"insights": eng.get_engagement_insights()})
