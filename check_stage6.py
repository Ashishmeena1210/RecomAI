import json
from recomai.config import MOVIE_CONFIG
from recomai.loaders.movies import load_movies
from recomai.hybrid_engine import HybridRecommender, format_results,_key

hyb = HybridRecommender(MOVIE_CONFIG).fit(load_movies("data"))

TITLES=["Titanic", "The Shawshank Redemption", "Interstellar","Toy Story","The Dark Knight"]

for title in TITLES:
    print(f"\n=== {title} ===")
    print(format_results(hyb.recommend_explained(title, k=5)))

print("\n--- JSON for one result ---")
print(json.dumps(hyb.recommend_explained("Titanic", k=1)[0], indent=2, ensure_ascii=False))

# faithfulness check: the contributions must add up to the score
for r in hyb.recommend_explained("Titanic", k=10):
    assert abs(sum(r["contributions"].values()) - r["score"]) < 0.005, r["title"]
print("\ncontributions add up to the score: OK")

# from recomai.hybrid_engine import _shared
# q = hyb.df.iloc[hyb._find("Interstellar")]
# c = hyb.df.iloc[hyb._find("The Martian")]
# print(type(q["genres"]), q["genres"], c["genres"])
# print("shared genres:  ", _shared(q["genres"], c["genres"]))
# print("shared keywords:", _shared(q["keywords"], c["keywords"]))

# q = hyb.df.iloc[hyb._find("Titanic")]
# print("Titanic genres:", q["genres"])

for title in TITLES:
    q = hyb.df.iloc[hyb._find(title)]
    for r in hyb.recommend_explained(title, k=10):
        c = hyb.df.iloc[hyb._find(r["title"])]
        for f, items in r["evidence"].items():
            got = {_key(x) for x in items}
            assert got <= {_key(x) for x in q[f]} and got <= {_key(x) for x in c[f]}, \
                (title, r["title"], f, items)
print("every reason is backed by both movies' data: OK")