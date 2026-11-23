"""Loads all three domains and checks each one against the DomainRecommender contract.
Run from the project root:  python check_all.py"""
import json
import time

from recomai.domains.base import DomainRecommender
from recomai.domains.books import BookDomain
from recomai.domains.movies import MovieDomain
from recomai.domains.songs import SongDomain

# (class, a search query for a title you know is in that domain's data)
DOMAINS = [(MovieDomain, "interstellar"), (BookDomain, "1984"), (SongDomain, "shayad")]
RESULT_KEYS = {"id", "title", "subtitle", "score", "reason", "meta"}


def check(domain, query):
    assert isinstance(domain, DomainRecommender)
    assert domain.name and domain.label, "name and label must be set"
    hits = domain.search(query)
    assert hits, f"search({query!r}) found nothing: pick a title that exists in this domain"
    assert {"id", "title", "subtitle", "match"} <= set(hits[0]), "search hit is missing keys"
    assert isinstance(hits[0]["id"], str), "ids must be strings"
    res = domain.recommend(hits[0]["id"], k=5)
    assert res, "recommend returned nothing"
    for r in res:
        assert RESULT_KEYS <= set(r), f"result is missing {RESULT_KEYS - set(r)}"
        assert isinstance(r["id"], str) and 0 <= r["score"] <= 1 and isinstance(r["reason"], list)
    assert hits[0]["id"] not in {r["id"] for r in res}, "recommended the item itself"
    json.dumps(res)                                      # the API must be able to serialize it
    schema = domain.filter_schema()
    assert all({"key", "label", "type"} <= set(f) for f in schema), "bad filter_schema entry"
    try:
        domain.recommend("no-such-id")
        raise AssertionError("unknown id must raise KeyError")
    except KeyError:
        pass
    return hits[0], res, schema


for cls, query in DOMAINS:
    t = time.time()
    d = cls()
    secs = time.time() - t
    hit, res, schema = check(d, query)
    print(f"{d.name:6s} OK  loaded in {secs:4.1f}s | {hit['title']} -> {[r['title'] for r in res[:3]]} "
          f"| filters: {[f['key'] for f in schema]} | diversity: {d.supports_diversity}")
print("\nall three domains satisfy the contract")