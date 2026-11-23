import pandas as pd

from recomai.movies.config import MOVIE_CONFIG
from recomai.domains.base import DomainRecommender
from recomai.movies.loader.movies import load_movies
from recomai.movies.pipeline import RecomAI


def _year(v):
    return str(int(v)) if pd.notna(v) else ""


class MovieDomain(DomainRecommender):
    name = "movies"
    label = "Movies"
    supports_diversity = True

    def __init__(self, data_dir="data"):
        self.rec = RecomAI(MOVIE_CONFIG).fit(load_movies(data_dir))
        df = self.rec.df
        self._title_by_id = dict(zip(df["id"].astype(str), df["title"]))

    def search(self, query, limit=5):
        hits = []
        for h in self.rec.search(query, limit=limit):
            row = self.rec.df.iloc[h["index"]]
            hits.append({"id": str(row["id"]), "title": row["title"],
                         "subtitle": _year(row["year"]), "match": h["match"]})
        return hits

    def recommend(self, item_id, k=10, filters=None, diversity=0.0):
        title = self._title_by_id.get(str(item_id))
        if title is None:
            raise KeyError(item_id)
        results = self.rec.recommend_pipeline(title, k=k, filters=filters, diversity=diversity)
        for r in results:
            r["subtitle"] = _year(r["meta"].get("year"))
        return results

    def filter_schema(self):
        df = self.rec.df
        return [
            {"key": "genres", "label": "Genres", "type": "multiselect",
             "options": sorted({g for gs in df["genres"] for g in gs})},
            {"key": "language", "label": "Language", "type": "select",
             "options": sorted(df["original_language"].dropna().unique().tolist())},
            {"key": "year_min", "label": "From year", "type": "number"},
            {"key": "year_max", "label": "To year", "type": "number"},
            {"key": "min_rating", "label": "Minimum rating", "type": "number"},
            {"key": "max_runtime", "label": "Max runtime (min)", "type": "number"},
        ]