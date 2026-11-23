import os
import unittest

from rest_framework.test import APISimpleTestCase


@unittest.skipUnless(os.getenv("RECOMAI_SMOKE") == "1",
                     "set RECOMAI_SMOKE=1 to run against the real engines")
class RealHubSmokeTests(APISimpleTestCase):

    def _first_id(self, domain, q):
        r = self.client.get(f"/api/domains/{domain}/search/", {"q": q, "limit": 1})
        self.assertEqual(r.status_code, 200)
        hits = r.json()["results"]
        self.assertTrue(hits, f"no hits for {q!r} in {domain}")
        return hits[0]["id"]

    def _recommend(self, domain, item_id, **body):
        return self.client.post(f"/api/domains/{domain}/recommend/",
                                {"item_id": item_id, **body}, format="json")

    def test_domains_and_diversity_flags(self):
        doms = {d["name"]: d for d in self.client.get("/api/domains/").json()["domains"]}
        self.assertEqual(set(doms), {"movies", "books", "songs"})
        self.assertTrue(doms["movies"]["supports_diversity"])
        self.assertFalse(doms["books"]["supports_diversity"])
        self.assertTrue(doms["songs"]["supports_diversity"])

    def test_same_response_shape_and_score_range(self):
        for domain, q in [("movies", "Toy Story"), ("books", "1984"),("songs", "love")]:
            r = self._recommend(domain, self._first_id(domain, q), k=5)
            self.assertEqual(r.status_code, 200)
            for item in r.json()["results"]:
                for key in ("id", "title", "subtitle", "score", "reason", "meta"):
                    self.assertIn(key, item)
                self.assertTrue(0 <= item["score"] <= 1)

    def test_typo_search(self):
        r = self.client.get("/api/domains/movies/search/", {"q": "intersteller"})
        self.assertIn("Interstellar", r.json()["results"][0]["title"])

    def test_movie_diversity_changes_results(self):
        iid = self._first_id("movies", "Interstellar")
        a = [x["id"] for x in self._recommend("movies", iid, k=8, diversity=0.0).json()["results"]]
        b = [x["id"] for x in self._recommend("movies", iid, k=8, diversity=0.7).json()["results"]]
        self.assertNotEqual(a, b)

    def test_movie_filters(self):
        iid = self._first_id("movies", "Interstellar")
        f = {"language": "en", "year_min": 2010, "min_rating": 7.0}
        r = self._recommend("movies", iid, k=5, filters=f)
        self.assertEqual(r.status_code, 200, r.content)
        for x in r.json()["results"]:
            m = x["meta"]
            self.assertEqual(m.get("original_language"), "en")
            self.assertGreaterEqual(m.get("year") or 0, 2010)
            self.assertGreaterEqual(m.get("vote_average") or 0, 7.0)

    def test_book_filters(self):
        iid = self._first_id("books", "1984")
        r = self._recommend("books", iid, k=10, filters={"year_min": 1990, "year_max": 2005})
        self.assertEqual(r.status_code, 200, r.content)
        for x in r.json()["results"]:
            if x["meta"].get("year"):
                self.assertTrue(1990 <= int(x["meta"]["year"]) <= 2005)

    def test_unregistered_domain_404(self):
        self.assertEqual(self._recommend("anime", "x").status_code, 404)

    def test_songs_search_and_recommend(self):
        iid = self._first_id("songs", "love")
        r = self._recommend("songs", iid, k=5, diversity=0.5)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["diversity_applied"], 0.5)   # songs supports diversity
        self.assertTrue(r.json()["results"])

    def test_songs_schema_filters_accepted(self):
        # Use the first select-type filter the schema advertises, so no key is guessed.
        schema = self.client.get("/api/domains/songs/schema/").json()
        sel = next((f for f in schema["filters"]
                    if f["type"] in ("select", "multiselect") and f.get("options")), None)
        if sel is None:
            self.skipTest("songs has no select filter with options")
        iid = self._first_id("songs", "love")
        value = sel["options"][0]
        if sel["type"] == "multiselect":
            value = [value]
        r = self._recommend("songs", iid, k=5, filters={sel["key"]: value})
        self.assertEqual(r.status_code, 200, r.content)