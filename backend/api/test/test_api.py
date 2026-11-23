from unittest.mock import patch

from rest_framework.test import APISimpleTestCase

from recomai.domains.base import DomainRecommender
from recomai.hub import RecomAIHub


class FakeMovies(DomainRecommender):
    name, label = "movies", "Movies"
    supports_diversity, default_diversity = True, 0.3

    def search(self, query, limit=5):
        return [{"id": "1", "title": "Interstellar", "subtitle": "2014", "match": 100}][:limit]

    def recommend(self, item_id, k=10, filters=None, diversity=0.0):
        if item_id != "1":
            raise KeyError(item_id)
        return [{"id": "2", "title": "Arrival", "subtitle": "2016", "score": 0.91,
                 "reason": ["Similar genre"], "meta": {"rating": float("nan"), "div": diversity}}]

    def filter_schema(self):
        return [{"key": "genre", "label": "Genre", "type": "select", "options": ["Sci-Fi"]}]


class FakeSongs(FakeMovies):
    name, label, supports_diversity = "songs", "Songs", False


class ApiTests(APISimpleTestCase):
    def setUp(self):
        hub = RecomAIHub().register(FakeMovies()).register(FakeSongs())
        p = patch("api.views.get_hub", return_value=hub)
        p.start()
        self.addCleanup(p.stop)

    def test_health(self):
        self.assertEqual(self.client.get("/api/health/").json(), {"status": "ok"})

    def test_domains(self):
        names = [d["name"] for d in self.client.get("/api/domains/").json()["domains"]]
        self.assertEqual(names, ["movies", "songs"])

    def test_schema(self):
        r = self.client.get("/api/domains/movies/schema/").json()
        self.assertEqual(r["filters"][0]["key"], "genre")

    def test_search(self):
        r = self.client.get("/api/domains/movies/search/", {"q": "intersteller"})
        self.assertEqual(r.json()["results"][0]["title"], "Interstellar")

    def test_search_requires_q(self):
        self.assertEqual(self.client.get("/api/domains/movies/search/").status_code, 400)

    def test_recommend_ok_and_nan_becomes_null(self):
        r = self.client.post("/api/domains/movies/recommend/",
                             {"item_id": "1", "k": 5, "diversity": 0.5}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["results"][0]["meta"]["rating"])
        self.assertEqual(r.json()["diversity_applied"], 0.5)

    def test_diversity_ignored_when_unsupported(self):
        r = self.client.post("/api/domains/songs/recommend/",
                             {"item_id": "1", "diversity": 0.9}, format="json")
        self.assertEqual(r.json()["diversity_applied"], 0.0)

    def test_unknown_item_404(self):
        r = self.client.post("/api/domains/movies/recommend/", {"item_id": "nope"}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_unknown_domain_404(self):
        self.assertEqual(self.client.get("/api/domains/anime/schema/").status_code, 404)

    def test_unknown_filter_400(self):
        r = self.client.post("/api/domains/movies/recommend/",
                             {"item_id": "1", "filters": {"colour": "red"}}, format="json")
        self.assertEqual(r.status_code, 400)