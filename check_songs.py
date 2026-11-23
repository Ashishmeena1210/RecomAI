import json
import time

from recomai.domains.songs import SongDomain

t = time.time()
d = SongDomain()                       # loads, cleans and fits
e = d._engine
print(f"songs ready: {len(e.titles)} tracks in {time.time() - t:.1f}s")
print("rows dropped by each cleaning step:", e.df.attrs.get("dropped"))
multi = sum(len(g) > 1 for g in e.df["genres"]) / len(e.df)
print(f"genres: {len(e._by_genre)} | tracks listed under several genres: {multi:.0%}")
print("sample titles:", e.df["track_name"].sample(5, random_state=1).tolist())

print("\n--- search (edit these to songs you know) ---")
for q in ["kesariya arijit", "kesaria", "hurt", "hurt johnny cash", "shayad", "shaiyad"]:
    t = time.time()
    hits = d.search(q)
    print(f"{q!r} ({time.time() - t:.2f}s) ->", [(h["title"], h["subtitle"], h["match"]) for h in hits[:3]])

QUERY = "shayad"                       # the song to get recommendations for
hits = d.search(QUERY)
assert hits, "no match: try a title from the sample list"
q = hits[0]
print(f"\n--- recommendations for {q['title']} | {q['subtitle']} ---")
t = time.time()
res = d.recommend(q["id"], k=10)
print(f"recommend took {time.time() - t:.3f}s")
for r in res[:6]:
    print(r["title"], "|", r["subtitle"], "|", r["meta"]["genres"], r["score"])
    print("    ", r["reason"])

assert q["id"] not in {r["id"] for r in res}                           # never the song itself
assert len({r["id"] for r in res}) == len(res)
assert len({(r["title"], r["subtitle"]) for r in res}) == len(res)     # no copies of the same track
json.dumps(res)                                                        # JSON-safe for the API

# no other version of the same song by the same artist (e.g. "Song - Reprise")
from recomai.songs.engine import _base_title
same_song = [r["title"] for r in res
             if _base_title(r["title"]) == _base_title(q["title"])
             and {a.strip().lower() for a in r["subtitle"].split(",")} & {a.strip().lower() for a in q["subtitle"].split(",")}]
print("other versions of the query song in the results:", same_song)
assert not same_song

genre = res[0]["meta"]["genres"][0]
res2 = d.recommend(q["id"], k=5, filters={"genres": [genre], "explicit": "no", "min_popularity": 20})
assert all(genre in r["meta"]["genres"] and not r["meta"]["explicit"] and r["meta"]["popularity"] >= 20
           for r in res2)
print(f"filters hold for {len(res2)} results")

res3 = d.recommend(q["id"], k=10, diversity=0.3)
assert res3[0]["id"] == res[0]["id"] and len(res3) == len(res)
print("diversity 0.3 list:", [r["title"] for r in res3])
print("OK")
