# -*- coding: utf-8 -*-
"""api/forecast.py — Content-volume and revenue trend forecasting endpoints."""
from flask import Blueprint, jsonify, request

from core import forecasting as fc
from core.cache import cached

bp = Blueprint("forecast", __name__, url_prefix="/api/forecast")


@bp.route("/volume")
@cached
def volume():
    country = request.args.get("country", "All")
    periods = request.args.get("periods", 3, type=int)
    return jsonify(fc.forecast_content_volume(country, periods=min(max(periods, 1), 5)))


@bp.route("/revenue")
@cached
def revenue():
    country = request.args.get("country", "All")
    periods = request.args.get("periods", 3, type=int)
    return jsonify(fc.forecast_revenue(country, periods=min(max(periods, 1), 5)))
