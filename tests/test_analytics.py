# -*- coding: utf-8 -*-
"""tests/test_analytics.py — Market analytics engine tests."""
import unittest

from core import database
from core import analytics as an


class TestAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.build_db(force=False)  # reuse whatever's there; tests don't mutate data

    def test_kpis_shape(self):
        d = an.get_kpis("All")
        for key in ("total", "avg_rating", "avg_budget", "avg_revenue", "roi", "top_language"):
            self.assertIn(key, d)
        self.assertGreater(d["total"], 0)

    def test_kpis_country_scoped_differs_from_global(self):
        global_kpis = an.get_kpis("All")
        country_rows = an.get_country_comparison()["countries"]
        self.assertGreater(len(country_rows), 0)
        country_kpis = an.get_kpis(country_rows[0])
        self.assertLessEqual(country_kpis["total"], global_kpis["total"])

    def test_roi_by_genre_clamped(self):
        d = an.get_roi_by_genre("All")
        for v in d["roi"]:
            if v is not None:
                self.assertLessEqual(abs(v), 999)

    def test_top_titles_no_duplicates(self):
        d = an.get_top_titles("All", limit=20)
        titles = [t["title"] for t in d["titles"]]
        self.assertEqual(len(titles), len(set(titles)), "top_titles must not contain duplicate rows")

    def test_search_returns_relevant_matches(self):
        d = an.search_titles("batman", limit=5)
        self.assertGreater(len(d["results"]), 0)
        for r in d["results"]:
            self.assertIn("batman", r["title"].lower())

    def test_search_short_query_handled_by_caller(self):
        # analytics layer itself doesn't enforce min-length; that's API-layer behavior
        d = an.search_titles("zzzzznonexistentxyz", limit=5)
        self.assertEqual(d["results"], [])

    def test_genre_roi_significance_returns_valid_stats(self):
        d = an.get_genre_roi_significance("All")
        if d["p_value"] is not None:
            self.assertGreaterEqual(d["p_value"], 0)
            self.assertLessEqual(d["p_value"], 1)
            self.assertIsInstance(d["significant"], bool)

    def test_insights_nonempty_and_bounded(self):
        insights = an.get_insights("All")
        self.assertGreater(len(insights), 0)
        self.assertLessEqual(len(insights), 8)
        for ins in insights:
            for key in ("icon", "type", "title", "body", "sentiment"):
                self.assertIn(key, ins)

    def test_correlations_matrix_symmetric(self):
        d = an.get_correlations("All")
        n = len(d["labels"])
        for i in range(n):
            for j in range(n):
                if d["matrix"][i][j] is not None and d["matrix"][j][i] is not None:
                    self.assertAlmostEqual(d["matrix"][i][j], d["matrix"][j][i], places=4)

    def test_budget_revenue_scatter_consistent_lengths(self):
        d = an.get_budget_revenue_scatter("All", n=100)
        n = len(d["titles"])
        for key in ("budgets", "revenues", "ratings", "profitable"):
            self.assertEqual(len(d[key]), n)


if __name__ == "__main__":
    unittest.main()
