# -*- coding: utf-8 -*-
"""tests/test_api.py — Flask endpoint integration tests (via test client)."""
import unittest

from app import create_app


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def _assert_json_200(self, path):
        resp = self.client.get(path)
        self.assertEqual(resp.status_code, 200, f"{path} returned {resp.status_code}: {resp.get_data(as_text=True)[:200]}")
        return resp.get_json()

    def test_index_renders(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Netflix", resp.data)

    def test_market_endpoints(self):
        for path in ["/api/kpis", "/api/growth", "/api/genres", "/api/roi-by-genre",
                     "/api/languages", "/api/language-roi", "/api/correlations",
                     "/api/yearly-trend", "/api/budget-revenue-scatter",
                     "/api/ratings-distribution", "/api/country-comparison",
                     "/api/genre-evolution", "/api/top-titles", "/api/insights",
                     "/api/stats/genre-roi-significance", "/api/countries"]:
            self._assert_json_200(path)

    def test_market_endpoints_with_country_filter(self):
        countries = self._assert_json_200("/api/countries")
        self.assertGreater(len(countries), 0)
        d = self._assert_json_200(f"/api/kpis?country={countries[0]}")
        self.assertGreater(d["total"], 0)

    def test_search_requires_min_length(self):
        d = self._assert_json_200("/api/search?q=a")
        self.assertEqual(d["results"], [])
        d2 = self._assert_json_200("/api/search?q=batman")
        self.assertGreater(len(d2["results"]), 0)

    def test_engagement_endpoints(self):
        for path in ["/api/engagement/kpis", "/api/engagement/top", "/api/engagement/by-genre",
                     "/api/engagement/by-country", "/api/engagement/trend", "/api/engagement/insights"]:
            self._assert_json_200(path)

    def test_recommend_endpoint(self):
        d = self._assert_json_200("/api/recommend?title=Inception")
        self.assertTrue(d["found"])
        resp = self.client.get("/api/recommend")
        self.assertEqual(resp.status_code, 400)

    def test_forecast_endpoints(self):
        for path in ["/api/forecast/volume", "/api/forecast/revenue"]:
            self._assert_json_200(path)

    def test_export_pdf(self):
        resp = self.client.get("/api/export/pdf?country=All")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "application/pdf")
        self.assertGreater(len(resp.data), 1000)

    def test_export_excel(self):
        resp = self.client.get("/api/export/excel?country=All")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.data), 1000)

    def test_admin_health(self):
        d = self._assert_json_200("/api/admin/health")
        self.assertEqual(d["status"], "ok")

    def test_404_returns_json(self):
        resp = self.client.get("/api/totally-not-a-real-route")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()["error"], "Not found")


if __name__ == "__main__":
    unittest.main()
