import numpy as np
from recomai.movies.config import MOVIE_CONFIG
from recomai.movies.loader.movies import load_movies
from recomai.movies.pipeline import RecomAI, TitleNotFound

rec = RecomAI(MOVIE_CONFIG).fit(load_movies("data"))


def show(results):
    for r in results:
        m = r["meta"]
        print(f"  {r['title']:42s} {r['score']:.3f}  {m.get('year')}  {m.get('original_language')}  "
              f"rating {m.get('vote_average')} ({m.get('vote_count')} votes)  {m.get('runtime')} min")


# print("=== 7a: fuzzy search ===")
# for q in ["intersteller", "the dark nite", "toy storey", "interstellar", "xyzzy"]:
#     try:
#         print(f"{q!r} -> {rec.df.loc[rec.resolve(q), 'title']}")
#     except TitleNotFound as e:
#         if e.suggestions:
#             print(f"{q!r} -> did you mean:", [(s["title"], s["match"]) for s in e.suggestions[:3]])
#         else:
#             print(f"{q!r} -> no close match")

# print("\n=== 7b: filters (Interstellar) ===")
# print("no filters:")
# show(rec.recommend_pipeline("Interstellar", k=5))
# F = dict(language="en", year_min=2010, min_rating=7, min_votes=100)
# print(f"with {F}:")
# res = rec.recommend_pipeline("Interstellar", k=10, filters=F)
# show(res)
# for r in res:                                   # the filter must really hold for every result
#     m = r["meta"]
#     assert m["original_language"] == "en" and m["year"] >= 2010
#     assert m["vote_average"] >= 7 and m["vote_count"] >= 100
# print("every result satisfies the filters: OK")
# print("short films only (<= 100 min):")
# show(rec.recommend_pipeline("Toy Story", k=5, filters=dict(max_runtime=100)))

print("\n=== 7c: diversity ===")
for q in ["The Dark Knight", "Interstellar", "Toy Story"]:
    print(f"\n{q}")
    for d in [0.0, 0.3, 0.5, 0.7]:
        res = rec.recommend_pipeline(q, k=10, diversity=d)
        avg = np.mean([r["score"] for r in res])
        print(f"  diversity={d}: avg score {avg:.3f} | intra-list similarity "
              f"{rec.intra_list_similarity(res):.3f}")
        print("    ", [r["title"] for r in res])