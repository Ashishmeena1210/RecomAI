import re
import unicodedata

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from recomai.books.config import BookConfig, BOOK_CONFIG
from recomai.domains.base import DomainRecommender, fuzzy_titles

FILTER_KEYS = {"author", "year_min", "year_max"}


def _norm(s) -> str:
    """Lower-case, strip accents, letters+digits only. Used only to compare authors."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


class CollaborativeBookRecommender(DomainRecommender):
    """Item-item collaborative filtering: cosine similarity on a (Book-Title x User-ID) rating matrix.

    id = ISBN of one canonical edition per title (the pivot table is indexed by title).
    """

    supports_diversity = False       # CF has no diversity mechanism; the argument is ignored
    default_diversity = 0.0

    def __init__(self, config: BookConfig = BOOK_CONFIG):
        self.config = config
        self.name = config.name
        self.label = config.label

    def fit(self, books: pd.DataFrame, pt: pd.DataFrame) -> "CollaborativeBookRecommender":
        """books: the full Books.csv table. pt: pivot table, rows = Book-Title, columns = User-ID, filled with 0."""
        c = self.config
        self.titles = pt.index.tolist()
        self.pt=pt
        self._X = pt.to_numpy(dtype=float)
        self._sim = cosine_similarity(self._X)

        # one metadata row per matrix row, built ONCE (no DataFrame scans per request)
        meta = books.drop_duplicates(c.title_col).set_index(c.title_col).reindex(self.titles)
        self._isbn = meta[c.isbn_col].astype(str).tolist()
        self._author = meta[c.author_col].fillna("").astype(str).tolist()
        self._author_norm = np.array([_norm(a) for a in self._author])
        self._publisher = meta[c.publisher_col].tolist()
        self._image = meta[c.image_col].fillna("").astype(str).tolist()
        year = pd.to_numeric(meta[c.year_col], errors="coerce")
        self._year = year.where((year >= 1000) & (year <= pd.Timestamp.now().year)).to_numpy()  # junk -> NaN

        self._id_to_pos = {isbn: i for i, isbn in enumerate(self._isbn)}
        return self

    # ---------- contract ----------
    def search(self, query: str, limit: int = 5) -> list[dict]:
        return [{"id": self._isbn[i], "title": t, "subtitle": self._author[i], "match": m}
                for i, t, m in fuzzy_titles(query, self.titles, limit=limit)]

    def recommend(self, item_id, k=10, filters=None, diversity=0.0) -> list[dict]:
        pos = self._id_to_pos.get(str(item_id))
        if pos is None:
            raise KeyError(f"ISBN '{item_id}' is not in the recommendable set; use search() first")
        sims = self._sim[pos].copy()
        sims[pos] = -np.inf                                   # never recommend the book itself
        sims[~self._filter_mask(filters or {})] = -np.inf     # filter BEFORE choosing the top k
        sims[sims <= 0] = -np.inf                             # only books that share at least one reader
        order = np.argsort(-sims)
        order = order[np.isfinite(sims[order])][:k]
        return [self._build_result(pos, int(j), float(sims[j])) for j in order]

    def filter_schema(self) -> list[dict]:
        authors = sorted({a for a in self._author if a})
        return [
            {"key": "author", "label": "Author", "type": "select", "options": authors},
            {"key": "year_min", "label": "Published after", "type": "number"},
            {"key": "year_max", "label": "Published before", "type": "number"},
        ]

    # ---------- internals ----------
    def _filter_mask(self, f: dict) -> np.ndarray:
        unknown = set(f) - FILTER_KEYS
        if unknown:
            raise ValueError(f"Unknown filters {sorted(unknown)}; valid: {sorted(FILTER_KEYS)}")
        mask = np.ones(len(self.titles), dtype=bool)
        if "author" in f:
            mask &= self._author_norm == _norm(f["author"])
        if "year_min" in f:
            mask &= self._year >= f["year_min"]          # missing year (NaN) -> excluded
        if "year_max" in f:
            mask &= self._year <= f["year_max"]
        return mask

    def _build_result(self, pos: int, j: int, score: float) -> dict:
        shared = int(((self._X[pos] > 0) & (self._X[j] > 0)).sum())    # readers who rated both
        reason = [f"{shared} readers in the data rated both books (rating-pattern similarity {score:.2f})"]
        if self._author_norm[pos] and self._author_norm[pos] == self._author_norm[j]:
            reason.insert(0, f"Same author: {self._author[j]}")
        year, pub = self._year[j], self._publisher[j]
        return {
            "id": self._isbn[j],
            "title": self.titles[j],
            "subtitle": self._author[j],
            "score": round(score, 4),
            "reason": reason,
            "meta": {
                "author": self._author[j],
                "year": int(year) if np.isfinite(year) else None,
                "publisher": pub if isinstance(pub, str) else None,
                "image_url": self._image[j],
            },
        }