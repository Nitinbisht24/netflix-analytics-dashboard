# -*- coding: utf-8 -*-
"""
core/forecasting.py — Simple, explainable forecasting.

Deliberately uses transparent methods (linear trend + a damped-trend
variant) rather than a black-box model, because the audience for a
content-strategy dashboard needs to be able to explain *why* the
forecast says what it says. Both methods are shown side by side; a
naive last-3-years-average is also included as a sanity baseline.
"""
import numpy as np

from core.database import q_rows
from core.analytics import _country_key


def _fit_linear(years: list, values: list):
    x = np.array(years, dtype=float)
    y = np.array(values, dtype=float)
    mask = ~np.isnan(y)
    x, y = x[mask], y[mask]
    if len(x) < 4:
        return None
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    std_err = float(np.std(resid)) if len(resid) > 2 else 0.0
    return {"slope": float(slope), "intercept": float(intercept), "std_err": std_err}


def forecast_content_volume(country: str, periods: int = 3) -> dict:
    """Forecast number-of-titles-released for the next `periods` years."""
    ck = _country_key(country)
    rows = q_rows("SELECT release_year, count FROM yearly_trend WHERE country=? ORDER BY release_year", (ck,))
    # Drop the most recent year if it looks like a partial/incomplete year
    # (far below the trailing average) so it doesn't drag the trendline down
    years = [r["release_year"] for r in rows]
    counts = [r["count"] for r in rows]
    if len(counts) >= 4 and counts[-1] < 0.5 * (sum(counts[-4:-1]) / 3):
        years, counts = years[:-1], counts[:-1]

    if len(years) < 4:
        return {"years": years, "actual": counts, "forecast_years": [], "forecast": [], "lower": [], "upper": [], "method": "insufficient_data"}

    fit = _fit_linear(years, counts)
    last_year = years[-1]
    future_years = [last_year + i for i in range(1, periods + 1)]
    forecast = [max(0, fit["intercept"] + fit["slope"] * fy) for fy in future_years]
    lower = [max(0, f - 1.28 * fit["std_err"]) for f in forecast]  # ~80% interval
    upper = [f + 1.28 * fit["std_err"] for f in forecast]

    baseline = float(np.mean(counts[-3:]))

    return {
        "years": years,
        "actual": counts,
        "forecast_years": future_years,
        "forecast": [round(f, 1) for f in forecast],
        "lower": [round(l, 1) for l in lower],
        "upper": [round(u, 1) for u in upper],
        "naive_baseline": round(baseline, 1),
        "method": "linear_trend",
        "slope_per_year": round(fit["slope"], 2),
    }


def forecast_revenue(country: str, periods: int = 3) -> dict:
    """Forecast average revenue per title (in $M) for the next `periods` years."""
    ck = _country_key(country)
    rows = q_rows("""SELECT release_year, avg_revenue FROM yearly_trend
                      WHERE country=? AND avg_revenue IS NOT NULL ORDER BY release_year""", (ck,))
    years = [r["release_year"] for r in rows]
    values = [(r["avg_revenue"] or 0) / 1e6 for r in rows]

    if len(years) < 4:
        return {"years": years, "actual": values, "forecast_years": [], "forecast": [], "method": "insufficient_data"}

    fit = _fit_linear(years, values)
    last_year = years[-1]
    future_years = [last_year + i for i in range(1, periods + 1)]
    forecast = [max(0, fit["intercept"] + fit["slope"] * fy) for fy in future_years]
    lower = [max(0, f - 1.28 * fit["std_err"]) for f in forecast]
    upper = [f + 1.28 * fit["std_err"] for f in forecast]

    return {
        "years": years,
        "actual": [round(v, 2) for v in values],
        "forecast_years": future_years,
        "forecast": [round(f, 2) for f in forecast],
        "lower": [round(l, 2) for l in lower],
        "upper": [round(u, 2) for u in upper],
        "method": "linear_trend",
        "slope_per_year": round(fit["slope"], 3),
    }
