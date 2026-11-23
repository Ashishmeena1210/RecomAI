import json
import random

from recomai.domains.books import BookDomain

d = BookDomain()                      # loads and fits: a few seconds
e = d._engine
print("matrix:", e.pt.shape)
print("raters per book:", (e.pt > 0).sum(axis=1).describe().round(1).to_dict())
print("sample titles:", random.sample(e.titles, 8))
print("accented titles:", sum("é" in t for t in e.titles))

QUERY = "1984"                        # change to a title from the sample list
hits = d.search(QUERY)
print(hits[:3])
assert hits, "no match: pick a title from the sample list"

res = d.recommend(hits[0]["id"], k=10)
for r in res[:5]:
    print(r["title"], "|", r["subtitle"], r["score"], r["reason"])
print("top-10 scores:", [r["score"] for r in res])

assert hits[0]["id"] not in {r["id"] for r in res}
assert all(r["score"] > 0 for r in res)
json.dumps(res)                       # must be JSON-safe for the API
res2 = d.recommend(hits[0]["id"], k=5, filters={"year_min": 1990})
assert all(r["meta"]["year"] is not None and r["meta"]["year"] >= 1990 for r in res2)
print("OK")