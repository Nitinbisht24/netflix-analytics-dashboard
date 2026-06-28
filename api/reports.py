# -*- coding: utf-8 -*-
"""api/reports.py — PDF / Excel executive report export endpoints."""
from datetime import datetime

from flask import Blueprint, request, send_file

from core import reports

bp = Blueprint("reports", __name__, url_prefix="/api/export")


def _safe_country_slug(country: str) -> str:
    label = country if country and country != "All" else "global"
    return "".join(c if c.isalnum() else "_" for c in label).strip("_").lower() or "global"


@bp.route("/pdf")
def export_pdf():
    country = request.args.get("country", "All")
    buf = reports.build_pdf_report(country)
    fname = f"netflix_analytics_{_safe_country_slug(country)}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=fname)


@bp.route("/excel")
def export_excel():
    country = request.args.get("country", "All")
    buf = reports.build_excel_report(country)
    fname = f"netflix_analytics_{_safe_country_slug(country)}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                      as_attachment=True, download_name=fname)
