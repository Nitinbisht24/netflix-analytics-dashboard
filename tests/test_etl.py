# -*- coding: utf-8 -*-
"""tests/test_etl.py — ETL cleaning-logic tests."""
import re
import unittest

from core import etl


class TestMovieMarketETL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = etl.load_movie_market()

    def test_loads_rows(self):
        self.assertGreater(len(self.df), 1000)

    def test_dropped_columns_absent(self):
        self.assertNotIn("rating", self.df.columns)
        self.assertNotIn("duration", self.df.columns)

    def test_no_explicit_content(self):
        title_hit = self.df["title"].fillna("").str.contains(etl._EXPLICIT_PATTERN, regex=True)
        desc_hit = self.df["description"].fillna("").str.contains(etl._EXPLICIT_PATTERN, regex=True)
        self.assertEqual(int((title_hit | desc_hit).sum()), 0)

    def test_roi_only_where_reliable_budget(self):
        # Anything below the $50k floor must NOT have an ROI value
        unreliable = self.df[self.df["budget"] < 50_000]
        self.assertTrue(unreliable["roi"].isna().all())
        # Titles above the floor with real revenue should have a finite ROI
        reliable = self.df[(self.df["budget"] >= 50_000) & (self.df["revenue"] > 0)]
        self.assertTrue(reliable["roi"].notna().all())

    def test_roi_no_extreme_outliers(self):
        # The $50k floor should keep every ROI within a sane band
        finite_roi = self.df["roi"].dropna()
        self.assertLess(finite_roi.abs().max(), 1_000_000)

    def test_country_exploded(self):
        # A multi-country title should appear on more than one row
        multi = self.df.groupby("title")["country"].nunique()
        self.assertTrue((multi > 1).any())

    def test_primary_genre_populated(self):
        self.assertTrue((self.df["primary_genre"] != "").all())

    def test_release_year_is_int_no_nulls(self):
        self.assertFalse(self.df["release_year"].isna().any())
        self.assertTrue((self.df["release_year"] >= 1900).all())


class TestEngagementETL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = etl.load_engagement()

    def test_loads_rows(self):
        self.assertGreater(len(self.df), 50)

    def test_primary_metric_set(self):
        self.assertTrue((self.df["primary_metric"].isin(["hours", "views", "none"])).all())
        # every row should have at least one real metric
        self.assertEqual(int((self.df["primary_metric"] == "none").sum()), 0)

    def test_no_fabricated_cross_metric(self):
        # if hours is null, primary_metric must not claim "hours"
        null_hours = self.df[self.df["hours_viewed_millions"].isna()]
        self.assertFalse((null_hours["primary_metric"] == "hours").any())

    def test_period_values_valid(self):
        valid_periods = set(etl.ENGAGEMENT_PERIOD_ORDER) | {"All-Time"}
        self.assertTrue(self.df["report_period"].isin(valid_periods).all())


if __name__ == "__main__":
    unittest.main()
