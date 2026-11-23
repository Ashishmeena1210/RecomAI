from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from recomai.movies.engine import  _squash
from recomai.movies.embedding_engine import EmbeddingRecommender
from collections import Counter

SEMANTIC_STRONG=0.70
SEMANTIC_OK=0.50

def _key(s):
    return s.replace(" ","").lower()

def _shared(a,b):
    """Items of list a that also appear in list b (original spelling kept)."""
    in_b = {_key(x) for x in b}
    return [x for x in a if _key(x) in in_b]

 
class HybridRecommender(EmbeddingRecommender):
    """Weighted combination of per-field similarities, with explanations."""

    def _shared_terms(self, i, j, top=3):
        prod = self._ov[i].multiply(self._ov[j]).tocoo()
        order = np.argsort(-prod.data)[:top]
        return [self._ov_terms[prod.col[o]] for o in order]
     
    def fit(self, df):
        self.df = df.reset_index(drop=True)
        self.blocks = {}
        for f in self.config.list_fields:
            tokens = self.df[f].apply(_squash)
            self.blocks[f] = TfidfVectorizer(analyzer=lambda t: t).fit_transform(tokens)
        self.blocks["semantic"]=self._vectorize()  #sentence embeddings(cached)
        idx = pd.Series(self.df.index, index=self.df[self.config.title_col].str.lower())
        self._idx = idx[~idx.index.duplicated()]
        self._freq = {f: Counter(k for items in self.df[f] for k in {_key(x) for x in items})
              for f in self.config.list_fields}

        # overview TF-IDF, used only to explain the semantic score
        ov = TfidfVectorizer(stop_words="english", min_df=2, max_df=0.05)
        self._ov = ov.fit_transform(self.df["overview"].astype(str))
        self._ov_terms = ov.get_feature_names_out()
        return self


    def _resolve(self,weights,profile):
        if weights is not None:
            w=weights
        elif profile is not None:
            w=self.config.profiles[profile]
        else:
            w=self.config.weights
        unknown=set(w)-set(self.blocks)
        if unknown:
            raise ValueError(f"Unknown weight Keys {sorted(unknown)}; valid: {sorted(self.blocks)}")
        return w

    def _rank(self,title,weights,profile):
        w=self._resolve(weights,profile)
        i=self._find(title)
        parts={f:cosine_similarity(self.blocks[f][i:i+1],self.blocks[f]).ravel() for f in w}
        norm=sum(w.values())
        total=sum(w[f] * parts[f] for f in w)/norm
        total[i]=-1
        return i,w,norm,parts,total            

    def recommend(self, title, k=10, weights=None,profile=None):
        i,w,norm,parts,total=self._rank(title,weights,profile)
        top = total.argsort()[::-1][:k]
        out = pd.DataFrame({
            self.config.title_col: self.df.loc[top, self.config.title_col].values,
            "score": total[top].round(3),
        })
        for f in w:                                     # per-field scores = future explanations
            out[f] = parts[f][top].round(2)
        return out


    def _reason(self, f, q, c, score, i, j):
        if f == "semantic":
            if score >= SEMANTIC_STRONG:
                lead = "Very similar story and themes"
            elif score >= SEMANTIC_OK:
                lead = "Similar story and themes"
            else:
                lead = "Somewhat related themes"
            terms = self._shared_terms(i, j)
            if terms:
                return f"{lead} (both plots mention: {', '.join(terms)})"
            return f"{lead} (embedding similarity {score:.2f})"
        shared = _shared(q[f], c[f])
        if not shared:
            return None
        identical = len(shared) == len(q[f]) == len(c[f])
        shared = sorted(shared, key=lambda x: self._freq[f][_key(x)])   # rarest first
        label = self.config.reason_labels.get(f, f"Shares {f}")
        if identical and label.startswith("Shares "):
            label = label.replace("Shares ", "Same ", 1)
        limit = 5 if f == "genres" else 3
        text = ", ".join(shared[:limit])
        if len(shared) > limit:
            text += f" (+{len(shared) - limit} more)"
        return f"{label}: {text}"


    def recommend_explained(self, title, k=10, weights=None, profile=None, max_reasons=4):
        i, w, norm, parts, total = self._rank(title, weights, profile)
        top = total.argsort()[::-1][:k]
        q = self.df.iloc[i]                             # the query movie
        results = []
        for j in top:
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
            results.append({
                "title": c[self.config.title_col],
                "score": round(float(total[j]), 3),
                "reason": reasons[:max_reasons],
                "evidence": evidence,
                "fields": {f: round(float(parts[f][j]), 2) for f in w},
                "contributions": {f: round(v, 3) for f, v in contrib.items()},
            })
        return results         

def format_results(results):
    lines = []
    for r in results:
        lines.append(f"{r['title']}: {r['score'] * 100:.0f}% match")
        if r["reason"]:
            lines.append("    Recommended because: " + "; ".join(r["reason"]))
    return "\n".join(lines)