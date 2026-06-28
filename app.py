# -*- coding: utf-8 -*-
"""
app.py — Application factory & entrypoint.

    python app.py                 # dev server on :5000
    gunicorn "app:create_app()"   # production (see README)

On first boot, builds the SQLite analytics DB from the raw CSVs (skipped
on subsequent boots unless REBUILD_DB_ON_START=1 or data/processed/ is
deleted) and warms up the in-memory recommender index.
"""
import logging
import time

from flask import Flask, jsonify, render_template

from config import Config


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    logging.basicConfig(
        level=logging.DEBUG if app.config["DEBUG"] else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("netflix_analytics")

    from core import database, recommender

    t0 = time.time()
    # database.build_db(force=app.config["REBUILD_DB_ON_START"])
    # recommender.build()
    logger.info("Startup data pipeline ready in %.2fs", time.time() - t0)

    from api.market import bp as market_bp
    from api.engagement import bp as engagement_bp
    from api.recommend import bp as recommend_bp
    from api.forecast import bp as forecast_bp
    from api.reports import bp as reports_bp
    from api.admin import bp as admin_bp

    for bp in (market_bp, engagement_bp, recommend_bp, forecast_bp, reports_bp, admin_bp):
        app.register_blueprint(bp)

    @app.route("/")
    def index():
        from core import analytics as an
        countries = sorted(an.get_country_comparison()["countries"])
        return render_template("index.html", countries=countries)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
