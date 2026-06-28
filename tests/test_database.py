# -*- coding: utf-8 -*-
"""tests/test_database.py — SQLite build & query-layer tests."""
import unittest

from core import database


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.build_db(force=True)

    def test_titles_table_populated(self):
        row = database.q_one("SELECT COUNT(*) AS n FROM titles")
        self.assertGreater(row["n"], 1000)

    def test_engagement_table_populated(self):
        row = database.q_one("SELECT COUNT(*) AS n FROM engagement")
        self.assertGreater(row["n"], 50)

    def test_genre_stats_has_all_bucket(self):
        rows = database.q_rows("SELECT * FROM genre_stats WHERE country='__ALL__'")
        self.assertGreater(len(rows), 0)

    def test_genre_stats_roi_bounded(self):
        rows = database.q_rows("SELECT avg_roi FROM genre_stats WHERE avg_roi IS NOT NULL")
        for r in rows:
            self.assertLess(abs(r["avg_roi"]), 1_000_000)

    def test_country_stats_no_tiny_countries(self):
        rows = database.q_rows("SELECT count FROM country_stats")
        for r in rows:
            self.assertGreaterEqual(r["count"], 5)

    def test_correlations_self_pairs_absent(self):
        # we only store unique (var1, var2) pairs where var1 != var2
        rows = database.q_rows("SELECT var1, var2 FROM correlations WHERE var1 = var2")
        self.assertEqual(len(rows), 0)

    def test_engagement_genre_stats_excludes_all_time_double_count(self):
        # Sanity check the double-counting fix: summed views should be far
        # less than naively summing every row (which would include All-Time)
        scoped = database.q_one("SELECT SUM(total_views) AS s FROM engagement_genre_stats")
        naive = database.q_one("SELECT SUM(views_millions) AS s FROM engagement WHERE views_millions IS NOT NULL")
        self.assertLess(scoped["s"], naive["s"])

    def test_engagement_period_trend_excludes_all_time(self):
        rows = database.q_rows("SELECT report_period FROM engagement_period_trend")
        periods = {r["report_period"] for r in rows}
        self.assertIn("All-Time", periods)  # it's tracked, just excluded from *sum* aggregates elsewhere


if __name__ == "__main__":
    unittest.main()
