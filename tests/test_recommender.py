# -*- coding: utf-8 -*-
"""tests/test_recommender.py — Content-based recommender tests."""
import unittest

from core import recommender as rec


class TestRecommender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rec.build()

    def test_known_title_found(self):
        d = rec.recommend("Inception", n=5)
        self.assertTrue(d["found"])
        self.assertEqual(len(d["results"]), 5)

    def test_results_exclude_query_itself(self):
        d = rec.recommend("Inception", n=8)
        titles = [r["title"] for r in d["results"]]
        self.assertNotIn("Inception", titles)

    def test_similarity_scores_descending(self):
        d = rec.recommend("Inception", n=8)
        sims = [r["similarity"] for r in d["results"]]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_unknown_title_handled_gracefully(self):
        d = rec.recommend("zzzznonexistenttitlexyz123", n=5)
        self.assertFalse(d["found"])
        self.assertEqual(d["results"], [])

    def test_no_explicit_content_in_results(self):
        from core import etl
        d = rec.recommend("Inception", n=8)
        for r in d["results"]:
            self.assertFalse(bool(etl._EXPLICIT_PATTERN.search(r["title"])))

    def test_seed_titles_returns_requested_count(self):
        titles = rec.random_seed_titles(6)
        self.assertEqual(len(titles), 6)


if __name__ == "__main__":
    unittest.main()
