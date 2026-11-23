import ast
from pathlib import Path
import pandas as pd

def _names(text, limit=None):
    try:
        items = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return []
    names = [i["name"] for i in items]
    return names[:limit] if limit else names

def _director(text):
    try:
        for m in ast.literal_eval(text):
            if m.get("job") == "Director":
                return [m["name"]]
    except (ValueError, SyntaxError):
        pass
    return []

def load_movies(data_dir):
    data_dir = Path(data_dir)
    movies = pd.read_csv(data_dir /"movies/tmdb_5000_movies.csv")
    credits = pd.read_csv(data_dir /"movies/tmdb_5000_credits.csv")
    credits = credits.rename(columns={"movie_id": "id"}).drop(columns=["title"])
    df = movies.merge(credits, on="id")
    df = df.dropna(subset=["overview"]).reset_index(drop=True)

    df["genres"] = df["genres"].apply(_names)
    df["keywords"] = df["keywords"].apply(_names)
    df["cast"] = df["cast"].apply(lambda x: _names(x, limit=4))
    df["director"] = df["crew"].apply(_director)
    df["year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year

    return df[["id", "title", "overview", "genres", "keywords", "cast", "director",
               "vote_average", "vote_count", "original_language", "year", "runtime"]]