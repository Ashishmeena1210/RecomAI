from abc import ABC, abstractmethod

from rapidfuzz import fuzz, process, utils


class DomainRecommender(ABC):
    name: str                      # URL slug: "movies" | "songs" | "books"
    label: str                     # display name: "Movies"
    supports_diversity = False     # the UI hides the diversity slider if False
    default_diversity = 0.0        # where the UI starts the slider

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Find items by (possibly misspelled) text. Each hit:
        {"id": str, "title": str, "subtitle": str, "match": 0-100}
        subtitle disambiguates same-named items: year for movies, artist for songs, author for books."""

    @abstractmethod
    def recommend(self, item_id: str, k: int = 10,
                  filters: dict | None = None, diversity: float = 0.0) -> list[dict]:
        """Items similar to item_id. Each result:
        {"id": str, "title": str, "subtitle": str,
         "score": float 0-1,        # similarity, only comparable within one list
         "reason": [str, ...],      # may be empty if the method can't explain
         "meta": {...}}             # free-form extras (year, rating, audio features, ...)
        Raise KeyError if item_id is unknown."""

    def filter_schema(self) -> list[dict]:
        """Filters this domain supports, so the UI can render them. Each:
        {"key": str, "label": str, "type": "select"|"multiselect"|"number",
         "options": [...]}          # options only for select / multiselect"""
        return []


def fuzzy_titles(query, titles, limit=5, min_score=70, band=15):
    """Typo-tolerant title search. Returns [(row_index, title, match 0-100), ...], best first."""
    hits = process.extract(query, titles, scorer=fuzz.WRatio, processor=utils.default_process,
                           limit=max(limit * 4, 20), score_cutoff=min_score)
    if not hits:
        return []
    best = max(s for _, s, _ in hits)
    hits = [h for h in hits if h[1] >= best - band]          # drop suggestions far behind the best
    n = len(utils.default_process(query))
    # ties: prefer the title whose length is closest to what was typed
    hits.sort(key=lambda h: (-round(h[1]), abs(len(utils.default_process(h[0])) - n), h[2]))
    return [(int(i), t, round(s)) for t, s, i in hits[:limit]]