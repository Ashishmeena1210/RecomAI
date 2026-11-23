import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors


def _squash(names):
    return [n.replace(" ", "").lower() for n in names]

class ContentRecommender:
    def __init__(self, config):
        self.config = config

    def _soup(self, row):
        parts = [str(row[f]).lower() for f in self.config.text_fields]
        for f in self.config.list_fields:
            parts += _squash(row[f])
        return " ".join(parts)

    def fit_tf_idf(self, df):
        self.df = df.reset_index(drop=True)
        soups = self.df.apply(self._soup, axis=1)
        self.vectorizer = TfidfVectorizer(**self.config.tfidf_params)
        self.matrix = self.vectorizer.fit_transform(soups)
        self.terms = self.vectorizer.get_feature_names_out()
        self.knn = NearestNeighbors(metric="cosine", algorithm="brute").fit(self.matrix)
        idx = pd.Series(self.df.index, index=self.df[self.config.title_col].str.lower())
        self._idx = idx[~idx.index.duplicated()]   # guard against duplicate titles
        return self

    def fit(self, df):
        self.df = df.reset_index(drop=True)
        self.matrix = self._vectorize()
        self.knn = NearestNeighbors(metric="cosine", algorithm="brute").fit(self.matrix)
        idx = pd.Series(self.df.index, index=self.df[self.config.title_col].str.lower())
        self._idx = idx[~idx.index.duplicated()]
        return self

    def _vectorize(self):
        soups = self.df.apply(self._soup, axis=1)
        self.vectorizer = TfidfVectorizer(**self.config.tfidf_params)
        matrix = self.vectorizer.fit_transform(soups)
        self.terms = self.vectorizer.get_feature_names_out()
        return matrix

    def _find(self, title):
        i = self._idx.get(title.lower())
        if i is None:
            raise KeyError(f"'{title}' not found")
        return i

    def recommend_cosine(self, title, k=10):
        i = self._find(title)
        scores = cosine_similarity(self.matrix[i], self.matrix).ravel()
        top = scores.argsort()[::-1][1:k + 1]
        return pd.DataFrame({
            self.config.title_col: self.df.loc[top, self.config.title_col].values,
            "score": scores[top].round(3),
        })

    def recommend(self, title, k=10):
        i = self._find(title)
        dist, ind = self.knn.kneighbors(self.matrix[i:i+1], n_neighbors=k + 1)
        dist, ind = dist.ravel(), ind.ravel()
        keep = ind != i                      # drop the query item by index, not by position
        dist, ind = dist[keep][:k], ind[keep][:k]
        return pd.DataFrame({
            self.config.title_col: self.df.loc[ind, self.config.title_col].values,
            "score": (1 - dist).round(3),   # distance -> similarity
        })

    def explain(self, title_a, title_b, top=8):
        a, b = self._find(title_a), self._find(title_b)
        contrib = self.matrix[a].multiply(self.matrix[b]).toarray().ravel()
        best = contrib.argsort()[::-1][:top]
        return [(self.terms[j], round(float(contrib[j]), 4))
                for j in best if contrib[j] > 0]