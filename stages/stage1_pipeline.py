import ast
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- Load & merge ----------
movies = pd.read_csv("data/tmdb_5000_movies.csv")
credits = pd.read_csv("data/tmdb_5000_credits.csv")
credits = credits.rename(columns={"movie_id": "id"}).drop(columns=["title"])
df = movies.merge(credits, on="id")

# ---------- Clean ----------
df = df[["id", "title", "overview", "genres", "keywords", "cast", "crew"]]
df = df.dropna(subset=["overview"]).reset_index(drop=True)

def parse_names(text, limit=None):
    """Turn a JSON-like string of dicts into a list of names."""
    try:
        items = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return []
    names = [i["name"] for i in items]
    return names[:limit] if limit else names

def get_director(text):
    try:
        for member in ast.literal_eval(text):
            if member.get("job") == "Director":
                return [member["name"]]
    except (ValueError, SyntaxError):
        pass
    return []

df["genres"] = df["genres"].apply(parse_names)
df["keywords"] = df["keywords"].apply(parse_names)
df["cast"] = df["cast"].apply(lambda x: parse_names(x, limit=4))  # top billed only
df["director"] = df["crew"].apply(get_director)

# ---------- Feature engineering ----------
def squash(names):
    """'Christopher Nolan' -> 'christophernolan' so it stays one token."""
    return [n.replace(" ", "").lower() for n in names]

def build_soup(row):
    parts = (
        squash(row["genres"]) + squash(row["keywords"])
        + squash(row["cast"]) + squash(row["director"])
    )
    return row["overview"].lower() + " " + " ".join(parts)

df["soup"] = df.apply(build_soup, axis=1)

# ---------- Vectorize ----------
tfidf = TfidfVectorizer(stop_words="english",max_features=20000,ngram_range=(1,1),min_df=2,max_df=0.8)
matrix = tfidf.fit_transform(df["soup"])
print(matrix.shape)

# ---------- Recommend ----------
title_to_idx = pd.Series(df.index, index=df["title"].str.lower())

def recommend(title, k=10):
    idx = title_to_idx.get(title.lower())
    if idx is None:
        return f"'{title}' not found"
    scores = cosine_similarity(matrix[idx], matrix).ravel()
    top = scores.argsort()[::-1][1:k + 1]  # skip itself
    return pd.DataFrame({"title": df.loc[top, "title"].values,
                         "score": scores[top].round(3)})

print(recommend("The Dark Knight"))

terms = tfidf.get_feature_names_out()

def explain(a, b, top=8):
    ia, ib = title_to_idx[a.lower()], title_to_idx[b.lower()]
    contrib = matrix[ia].multiply(matrix[ib]).toarray().ravel()
    best = contrib.argsort()[::-1][:top]
    return [(terms[i], round(float(contrib[i]), 4)) for i in best if contrib[i] > 0]

print(explain("The Dark Knight", "Interstellar"))
