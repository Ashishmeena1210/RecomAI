import re
from collections import defaultdict

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process, utils

from recomai.songs.config import SONG_CONFIG, SongConfig

FILTER_KEYS = {"genres", "explicit", "min_popularity"}

# feature -> (phrase when clearly above average, phrase when clearly below average)
TRAIT_LABELS = {
    "valence":          ("positive mood", "negative mood"),
    "danceability":     ("danceable", "not very danceable"),
    "energy":           ("high energy", "low energy"),
    "tempo":            ("fast tempo", "slow tempo"),
    "acousticness":     ("acoustic", "low acousticness"),
    "liveness":         ("live-sounding", "not live-sounding"),
    "speechiness":      ("lots of spoken words", "little spoken word"),
    "instrumentalness": ("instrumental", "vocal"),
    "loudness":         ("loud", "quiet"),
}


def _split_artists(raw):
    return [a.strip() for a in str(raw).split(";") if a.strip()]


def _base_title(title):
    """Title without '(From ...)' / '[Remastered]' groups and without a '- Reprise' style suffix."""
    t = re.sub(r"\s*[\(\[].*?[\)\]]", "", str(title).lower())
    t = t.split(" - ")[0]
    return re.sub(r"\s+", " ", t).strip()


class AudioSongRecommender:
    """Cosine similarity on standardized audio features, then a genre / shared-artist bonus.

    This is the method from the songs notebook: StandardScaler -> cosine nearest neighbours over
    all tracks -> top `pool` -> score = 0.70*(1 - cosine distance) + 0.20*same genre + 0.10*shared artist.
    (The notebook's KMeans clusters and per-cluster models were never used by its recommend function,
    so they are not part of this engine.)
    """

    def __init__(self, config: SongConfig = SONG_CONFIG):
        self.config = config

    def fit(self, df: pd.DataFrame) -> "AudioSongRecommender":
        c = self.config
        self.df = df.reset_index(drop=True)
        n = len(self.df)

        X = self.df[list(c.features)].to_numpy(dtype=float)
        std = X.std(axis=0)
        self._Z = (X - X.mean(axis=0)) / np.where(std > 0, std, 1.0)   # same as StandardScaler
        norm = np.linalg.norm(self._Z, axis=1, keepdims=True)
        self._U = self._Z / np.maximum(norm, 1e-12)                    # unit rows: dot product = cosine

        self.titles = self.df[c.title_col].astype(str).tolist()
        artists = [_split_artists(a) for a in self.df[c.artist_col]]
        self._artists = [", ".join(a) for a in artists]
        self._artist_sets = [{x.lower() for x in a} for a in artists]

        # search text, normalized ONCE (lower-case, letters and digits only)
        self._title_norm = [utils.default_process(t) for t in self.titles]
        self._artist_norm = [utils.default_process(a) for a in self._artists]

        # all genres of each track (the loader merges the duplicate per-genre rows)
        if "genres" in self.df.columns:
            genre_lists = self.df["genres"].tolist()
        else:
            genre_lists = [[g] for g in self.df[c.genre_col].astype(str)]
        self._genre_sets = [{str(g).lower() for g in gl} for gl in genre_lists]
        self._by_genre = defaultdict(list)
        for i, gs in enumerate(self._genre_sets):
            for g in gs:
                self._by_genre[g].append(i)
        self._primary_genre = self.df[c.genre_col].astype(str).tolist()

        # other versions of the same song
        self._base = [_base_title(t) for t in self.titles]
        self._by_base = defaultdict(list)
        for i, b in enumerate(self._base):
            if b:
                self._by_base[b].append(i)

        self._pop = self.df[c.popularity_col].to_numpy(dtype=float)
        self._explicit = (self.df[c.explicit_col].astype(str).str.lower()
                          .isin(["true", "1", "yes"]).to_numpy())
        self._ids = self.df[c.id_col].astype(str).tolist()
        self._id_to_pos = {i: p for p, i in enumerate(self._ids)}

        # which traits are distinctive? share of ALL tracks that lies >= trait_z on each side
        self._trait_ok = {}
        for k, f in enumerate(c.features):
            self._trait_ok[f] = ((self._Z[:, k] >= c.trait_z).mean() <= c.trait_max_share,
                                 (self._Z[:, k] <= -c.trait_z).mean() <= c.trait_max_share)
        return self

    # ---------- contract ----------
    def search(self, query, limit=5, min_score=70, band=15):
        """Typo-tolerant search on the TITLE. Words that match an artist break ties between songs with
        similar titles ('kesariya arijit' prefers the Arijit Singh 'Kesariya'). Ties then resolve to the
        most popular track, because the table is sorted by popularity.

        (Matching 'title + artists' as one string does not work: every song by the typed artist scores
        the same as the song you meant, because WRatio gives full marks to any shared word.)"""
        q = utils.default_process(query)
        if not q:
            return []
        try:                    # all CPU cores; titles were normalized once in fit()
            scores = process.cdist([q], self._title_norm, scorer=fuzz.WRatio, processor=None,
                                   score_cutoff=min_score, dtype=np.uint8, workers=-1)[0]
        except TypeError:       # older rapidfuzz without the dtype / workers arguments
            scores = process.cdist([q], self._title_norm, scorer=fuzz.WRatio, processor=None,
                                   score_cutoff=min_score)[0]
        best = int(scores.max())
        if best < min_score:
            return []
        cand = np.flatnonzero(scores >= best - band)
        qtok = set(q.split())

        def key(i):
            extra = qtok - set(self._title_norm[i].split())       # query words the title does not contain
            artist_hits = len(extra & set(self._artist_norm[i].split()))
            return (-int(scores[i]), -artist_hits, i)

        top = sorted((int(i) for i in cand), key=key)[:limit]
        return [{"id": self._ids[i], "title": self.titles[i],
                 "subtitle": self._artists[i], "match": int(scores[i])} for i in top]

    def recommend(self, item_id, k=10, filters=None, diversity=0.0):
        c = self.config
        pos = self._id_to_pos.get(str(item_id))
        if pos is None:
            raise KeyError(f"track '{item_id}' not found; use search() first")
        if not 0 <= diversity < 1:
            raise ValueError("diversity must be in [0, 1)")

        cos = self._U @ self._U[pos]                          # cosine to every track
        mask = self._filter_mask(filters or {})               # filter BEFORE choosing the pool
        mask[pos] = False                                     # never recommend the track itself
        if c.exclude_versions and self._base[pos]:
            for j in self._by_base[self._base[pos]]:          # other versions of the same song
                if self._artist_sets[j] & self._artist_sets[pos]:
                    mask[j] = False
        n_pool = min(c.pool, int(mask.sum()))
        if n_pool == 0:
            return []
        masked = np.where(mask, cos, -np.inf)
        idx = np.argpartition(-masked, n_pool - 1)[:n_pool]   # nearest tracks by audio

        qgenres = self._genre_sets[pos]
        genre_match = np.array([bool(self._genre_sets[j] & qgenres) for j in idx], dtype=float)
        artist_match = np.array([bool(self._artist_sets[j] & self._artist_sets[pos]) for j in idx],
                                dtype=float)
        score = c.w_audio * cos[idx] + c.w_genre * genre_match + c.w_artist * artist_match
        order = np.argsort(-score)
        idx, score = idx[order], score[order]

        if diversity > 0 and len(idx) > 1:
            chosen = self._mmr(idx, score, diversity, k)
        else:
            chosen = list(range(min(k, len(idx))))
        return [self._item(pos, int(idx[p]), float(score[p]), float(cos[idx[p]])) for p in chosen]

    def filter_schema(self):
        return [
            {"key": "genres", "label": "Genres", "type": "multiselect",
             "options": sorted(self._by_genre)},
            {"key": "explicit", "label": "Explicit lyrics", "type": "select",
             "options": ["yes", "no"]},
            {"key": "min_popularity", "label": "Minimum popularity (0-100)", "type": "number"},
        ]

    # ---------- internals ----------
    def _filter_mask(self, f):
        unknown = set(f) - FILTER_KEYS
        if unknown:
            raise ValueError(f"Unknown filters {sorted(unknown)}; valid: {sorted(FILTER_KEYS)}")
        mask = np.ones(len(self.titles), dtype=bool)
        if "genres" in f:
            wanted = [f["genres"]] if isinstance(f["genres"], str) else list(f["genres"])
            hit = np.zeros(len(self.titles), dtype=bool)          # any of the track's genres matches
            for g in wanted:
                hit[np.array(self._by_genre.get(str(g).lower(), []), dtype=int)] = True
            mask &= hit
        if "explicit" in f:
            want = str(f["explicit"]).lower() in ("yes", "true", "1")
            mask &= self._explicit == want
        if "min_popularity" in f:
            mask &= self._pop >= f["min_popularity"]
        return mask

    def _mmr(self, idx, score, diversity, k):
        """Maximal Marginal Relevance on the ranked pool. Same scale for both terms: the
        redundancy penalty uses the audio part of the score (w_audio * cosine)."""
        sim = self.config.w_audio * (self._U[idx] @ self._U[idx].T)
        lam = 1 - diversity
        chosen, rest = [0], list(range(1, len(idx)))
        while rest and len(chosen) < k:
            red = sim[np.ix_(rest, chosen)].max(axis=1)
            best = rest[int((lam * score[rest] - (1 - lam) * red).argmax())]
            chosen.append(best)
            rest.remove(best)
        return chosen

    def _shared_traits(self, pos, j, top=3):
        """Distinctive audio traits where BOTH tracks are clearly above (or below) average."""
        zq, zj = self._Z[pos], self._Z[j]
        found = []
        for k, f in enumerate(self.config.features):
            if f not in TRAIT_LABELS:
                continue
            hi, lo = TRAIT_LABELS[f]
            a, b = zq[k], zj[k]
            strength = min(abs(a), abs(b))
            if a * b > 0 and strength >= self.config.trait_z and self._trait_ok[f][0 if a > 0 else 1]:
                found.append((strength, hi if a > 0 else lo))
        found.sort(reverse=True)
        return [label for _, label in found[:top]]

    def _item(self, pos, j, score, cos):
        c = self.config
        row = self.df.iloc[j]
        reason = []
        shared = [a for a in _split_artists(row[c.artist_col]) if a.lower() in self._artist_sets[pos]]
        if shared:
            reason.append("Shares artist: " + ", ".join(shared))
        genres = sorted(self._genre_sets[j] & self._genre_sets[pos])
        if genres:
            reason.append(("Shares genre: " if len(genres) == 1 else "Shares genres: ") + ", ".join(genres[:3]))
        traits = self._shared_traits(pos, j)
        if traits:
            reason.append(f"Similar sound: {', '.join(traits)} (audio similarity {cos:.2f})")
        else:
            reason.append(f"Close audio profile (audio similarity {cos:.2f})")

        album, dur = row[c.album_col], row[c.duration_col]
        return {
            "id": self._ids[j],
            "title": self.titles[j],
            "subtitle": self._artists[j],
            "score": round(float(np.clip(score, 0.0, 1.0)), 3),
            "reason": reason,
            "meta": {
                "genre": self._primary_genre[j],
                "genres": sorted(self._genre_sets[j]),
                "album": str(album) if pd.notna(album) and str(album) else None,
                "popularity": int(self._pop[j]),
                "explicit": bool(self._explicit[j]),
                "duration_s": int(round(float(dur) / 1000)) if pd.notna(dur) else None,
                "audio": {f: round(float(row[f]), 3) for f in c.features},
                "spotify_url": f"https://open.spotify.com/track/{self._ids[j]}",
            },
        }
