# -*- coding: utf-8 -*-
"""tests/test_engagement.py — Real Netflix engagement-data analytics tests."""
import unittest

from core import database
from core import engagement as eng


class TestEngagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.build_db(force=False)

    def test_kpis_shape(self):
        d = eng.get_engagement_kpis()
        for key in ("total_titles", "sum_hours_viewed_millions", "sum_views_millions",
                    "top_country_by_views", "top_genre_by_views"):
            self.assertIn(key, d)
        self.assertGreater(d["total_titles"], 0)

    def test_top_by_views_sorted_descending(self):
        d = eng.get_engagement_top("views", limit=20)
        values = [t["views_millions"] for t in d["titles"] if t["views_millions"] is not None]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_top_by_hours_sorted_descending(self):
        d = eng.get_engagement_top("hours", limit=20)
        values = [t["hours_viewed_millions"] for t in d["titles"] if t["hours_viewed_millions"] is not None]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_top_content_type_filter(self):
        d = eng.get_engagement_top("views", content_type="Movie", limit=50)
        for t in d["titles"]:
            self.assertEqual(t["content_type"], "Movie")

    def test_by_genre_no_negative_totals(self):
        d = eng.get_engagement_by_genre()
        for v in d["total_views"]:
            self.assertGreaterEqual(v, 0)

    def test_trend_chronological_order_excludes_all_time(self):
        d = eng.get_engagement_trend()
        self.assertNotIn("All-Time", d["periods"])
        self.assertEqual(d["periods"], sorted(d["periods"]))

    def test_insights_nonempty(self):
        insights = eng.get_engagement_insights()
        self.assertGreater(len(insights), 0)


if __name__ == "__main__":
    unittest.main()
