from recomai.config import MOVIE_CONFIG
from recomai.loaders.movies import load_movies
from recomai.hybrid_engine import HybridRecommender

hyb = HybridRecommender(MOVIE_CONFIG).fit(load_movies("data"))

#for title in ["Interstellar", "The Dark Knight", "Toy Story"]:
    #print(f"\n=== {title} (default weights) ===")
    #print(hyb.recommend(title).to_string())

#print("\n=== Interstellar, overview only ===")
#print(hyb.recommend("Interstellar", weights=dict(overview=1.0)).to_string())

w = dict(semantic=.50, genres=.20, keywords=.15, director=.10, cast=.05)
for t in ["The Shawshank Redemption", "Titanic"]:
    print(t); print(hyb.recommend(t, weights=w).to_string())

#full = hyb.recommend("The Dark Knight", k=4800)
#print(full[full["title"].isin(["Batman Returns", "Batman", "Batman Forever"])])