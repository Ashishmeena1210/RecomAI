import pandas as pd
from recomai.config import MOVIE_CONFIG
from recomai.loaders.movies import load_movies
from recomai.engine import ContentRecommender
from recomai.embedding_engine import EmbeddingRecommender

df = load_movies("data")
tfidf = ContentRecommender(MOVIE_CONFIG).fit(df)
emb = EmbeddingRecommender(MOVIE_CONFIG).fit(df)

#for title in ["Interstellar", "The Dark Knight", "Toy Story"]:
#    t, e = tfidf.recommend(title), emb.recommend(title)
#    print(f"\n=== {title} ===")
#    print(pd.concat([t.add_prefix("tfidf_"), e.add_prefix("emb_")], axis=1).to_string())
#    print("overlap:", len(set(t["title"]) & set(e["title"])), "of 10")

print(emb.recommend("The Shawshank Redemption"))
print(emb.recommend("Avengers: Age of Ultron"))
print(emb.recommend("Titanic"))
print(emb.recommend("Harry Potter and the Order of the Phoenix"))