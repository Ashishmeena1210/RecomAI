import time
from recomai.config import MOVIE_CONFIG
from recomai.loaders.movies import load_movies
from recomai.engine import ContentRecommender

rec = ContentRecommender(MOVIE_CONFIG).fit(load_movies("data"))

for title in ["Interstellar", "The Dark Knight", "Toy Story"]:
    a, b = rec.recommend(title), rec.recommend_cosine(title)
    print(title, "-> same titles:", list(a.iloc[:, 0]) == list(b.iloc[:, 0]),
          "| same scores:", a["score"].equals(b["score"]))

def bench(fn, n=100):
    t = time.perf_counter()
    for _ in range(n):
        fn("Interstellar")
    return (time.perf_counter() - t) / n * 1000

print(f"KNN:    {bench(rec.recommend):.2f} ms/query")
print(f"cosine: {bench(rec.recommend_cosine):.2f} ms/query")