import re
import unicodedata

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process, utils
from sklearn.metrics.pairwise import cosine_similarity

from recomai.movies.hybrid_engine import HybridRecommender, _key, _shared

FILTER_KEYS = {"genres", "language", "year_min", "year_max",
               "min_rating", "min_votes", "max_runtime"}
FILTER_COLUMNS = ["vote_average", "vote_count", "original_language", "year", "runtime"]
INT_COLUMNS = {"year", "vote_count", "runtime"}


def _norm(s):
    """Lower-case, strip accents, keep only letters and digits."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


class TitleNotFound(KeyError):
    """Raised when a title can't be matched; carries 'did you mean' suggestions."""

    def __init__(self, query, suggestions):
        super().__init__(query)
        self.query = query
        self.suggestions = suggestions

    def __str__(self):
        names = ", ".join(s["title"] for s in self.suggestions[:3])
        return f"'{self.query}' not found" + (f". Did you mean: {names}?" if names else "")


class RecomAI(HybridRecommender):
    """Hybrid recommender + fuzzy title search + filters + diversity."""

    def fit(self, df):
        super().fit(df)
        self._norm_titles = {}
        for i, t in enumerate(self.df[self.config.title_col]):
            self._norm_titles.setdefault(_norm(t), i)
        return self

    # ---------- 7a: title search ----------
    def search(self, query, limit=5, min_score=50):
        titles = self.df[self.config.title_col].tolist()
        hits = process.extract(query, titles, scorer=fuzz.WRatio,
                               processor=utils.default_process,
                               limit=limit, score_cutoff=min_score)
        return [{"title": t, "match": round(s), "index": int(i)} for t, s, i in hits]

    def resolve(self, query):
        i = self._norm_titles.get(_norm(query))
        if i is None:
            raise TitleNotFound(query, self.search(query))
        return i

    def _find(self, title):
        # overrides the parent, so every inherited method gets forgiving matching too
        return self.resolve(title)

    # ---------- 7b: filters ----------
    def _filter_mask(self, filters):
        n = len(self.df)
        mask = np.ones(n, dtype=bool)
        if not filters:
            return mask
        unknown = set(filters) - FILTER_KEYS
        if unknown:
            raise ValueError(f"Unknown filters {sorted(unknown)}; valid: {sorted(FILTER_KEYS)}")
        missing = [c for c in FILTER_COLUMNS if c not in self.df.columns]
        if missing:
            raise ValueError(f"Filters need columns {missing}: update load_movies to keep them")
        d = self.df
        if "genres" in filters:
            wanted = {_key(g) for g in filters["genres"]}
            mask &= d["genres"].apply(lambda gs: any(_key(g) in wanted for g in gs)).to_numpy()
        if "language" in filters:
            langs = filters["language"]
            langs = [langs] if isinstance(langs, str) else list(langs)
            mask &= d["original_language"].isin(langs).to_numpy()
        if "year_min" in filters:
            mask &= (d["year"] >= filters["year_min"]).to_numpy()
        if "year_max" in filters:
            mask &= (d["year"] <= filters["year_max"]).to_numpy()
        if "min_rating" in filters:
            mask &= (d["vote_average"] >= filters["min_rating"]).to_numpy()
            mask &= (d["vote_count"] >= filters.get("min_votes", 50)).to_numpy()
        elif "min_votes" in filters:
            mask &= (d["vote_count"] >= filters["min_votes"]).to_numpy()
        if "max_runtime" in filters:
            mask &= ((d["runtime"] > 0) & (d["runtime"] <= filters["max_runtime"])).to_numpy()
        return mask

    # ---------- 7c: diversity ----------
    def _mmr(self, candidates, rel, w, norm, diversity, k):
        """candidates: row indices, best first. rel: their relevance scores."""
        lam = 1 - diversity
        pair = sum(w[f] * cosine_similarity(self.blocks[f][candidates]) for f in w) / norm
        chosen = [0]                                   # the most relevant item always goes first
        remaining = list(range(1, len(candidates)))
        while remaining and len(chosen) < k:
            redundancy = pair[np.ix_(remaining, chosen)].max(axis=1)
            score = lam * rel[remaining] - (1 - lam) * redundancy
            best = remaining[int(score.argmax())]
            chosen.append(best)
            remaining.remove(best)
        return [int(candidates[p]) for p in chosen]

    def intra_list_similarity(self, results, weights=None, profile=None):
        """Average pairwise similarity inside a result list (lower = more diverse)."""
        w = self._resolve(weights, profile)
        idx = [self._find(r["title"]) for r in results]
        n = len(idx)
        if n < 2:
            return 0.0
        pair = sum(w[f] * cosine_similarity(self.blocks[f][idx]) for f in w) / sum(w.values())
        np.fill_diagonal(pair, 0)
        return float(pair.sum() / (n * (n - 1)))

    # ---------- the full pipeline ----------
    def recommend_pipeline(self, title, k=10, filters=None, diversity=0.0,
                           weights=None, profile=None, pool=50, max_reasons=4):
        if not 0 <= diversity < 1:
            raise ValueError("diversity must be in [0, 1)")
        i, w, norm, parts, total = self._rank(title, weights, profile)
        total[i] = -np.inf                                   # never recommend the query itself
        total[~self._filter_mask(filters)] = -np.inf          # filter BEFORE choosing the top k
        order = total.argsort()[::-1]
        order = order[np.isfinite(total[order])][:max(pool, k)]
        if len(order) == 0:
            return []
        if diversity > 0 and len(order) > 1:
            chosen = self._mmr(order, total[order], w, norm, diversity, k)
        else:
            chosen = [int(j) for j in order[:k]]
        return self._explain_items(i, chosen, w, norm, parts, total, max_reasons)

    def _explain_items(self, i, js, w, norm, parts, total, max_reasons):
        q = self.df.iloc[i]
        results = []
        for j in js:
            c = self.df.iloc[j]
            contrib = {f: w[f] * float(parts[f][j]) / norm for f in w}
            reasons, evidence = [], {}
            for f in sorted(contrib, key=contrib.get, reverse=True):
                if contrib[f] <= 0:
                    continue
                text = self._reason(f, q, c, float(parts[f][j]), i, j)
                if text:
                    reasons.append(text)
                if f != "semantic":
                    shared = _shared(q[f], c[f])
                    if shared:
                        evidence[f] = shared
            meta = {}
            for col in FILTER_COLUMNS:
                if col in self.df.columns:
                    v = c[col]
                    if pd.isna(v):
                        v = None
                    elif col in INT_COLUMNS:
                        v = int(v)
                    elif hasattr(v, "item"):
                        v = v.item()
                    meta[col] = v
            results.append({
                "id":str(c["id"]),
                "title": c[self.config.title_col],
                "score": round(float(total[j]), 3),
                "reason": reasons[:max_reasons],
                "evidence": evidence,
                "meta": meta,
                "fields": {f: round(float(parts[f][j]), 2) for f in w},
                "contributions": {f: round(v, 3) for f, v in contrib.items()},
            })
        return results