import numpy as np
from recomai.config import MOVIE_CONFIG
from recomai.loaders.movies import load_movies
from recomai.engine import ContentRecommender
from recomai.embedding_engine import EmbeddingRecommender
from recomai.hybrid_engine import HybridRecommender

TRUTH = {
    "Interstellar": {"The Martian","Inception","The Matrix","Oblivion","Contact","The Fountain","The Prestige","Gravity","2001: A Space Odyssey"},
    "The Dark Knight": {"The Dark Knight Rises", "Batman Begins","The Departed","Se7en","The Prestige","Shutter Island","V for Vendetta","Nightcrawler","Zodiac","No Country for Old Men"},
    "Toy Story": {"Toy Story 2", "Toy Story 3", "Monsters, Inc.", "Finding Nemo",
                  "The Incredibles", "Up", "Inside Out","WALLÂ·E",
                  "How to Train Your Dragon 2"},
    # "Avengers: Age of Ultron":{},
    "Titanic":{"The Notebook","Atonement","The Curious Case of Benjamin Button","The Great Gatsby","Pride & Prejudice","Moulin Rouge!",
               "Pearl Harbor","The Time Traveler's Wife","Dear John","The English Patient"},
    # "Harry Potter and the Order of the Phoenix":{},
    "The Shawshank Redemption":{"The Green Mile","Forrest Gump","Catch Me If You Can","A Beautiful Mind","The Pursuit of Happyness",
                  "Slumdog Millionaire","Life Is Beautiful","12 Years a Slave","The Terminal"},
}

df=load_movies("data")
tfidf=ContentRecommender(MOVIE_CONFIG).fit(df)
emb=EmbeddingRecommender(MOVIE_CONFIG).fit(df)
hybrid=HybridRecommender(MOVIE_CONFIG).fit(df)


hybrid.blocks["semantic"]=emb.matrix

known=tfidf._idx
for q in list(TRUTH):
  missing=[t for t in {q,*TRUTH[q]} if t.lower() not in known]
  if missing:
    print("Not in the Dataset :",q,missing)
  TRUTH[q]={t for t in TRUTH[q] if t.lower() in known}  

def evaluate(recommend,k=10,verbose=False):
  p,r=[],[]
  for q,rel in TRUTH.items():
    got=set(recommend(q,k=k)["title"])
    hit=len(got & rel)
    p.append(hit/k)
    r.append(hit/len(rel))
    if verbose:
        print(f"  {q:20s} P={hit/k:.2f} R={hit/len(rel):.2f}  found: {sorted(got & rel)}")
  return round(np.mean(p),3),round(np.mean(r),3)

runs={
  "tfidf":tfidf.recommend,
  "embeddings (all fields)":emb.recommend,
}    

WEIGHTS={
  "hybrid: doc specific":dict(genres=.30,overview=.25,keywords=.20,director=.15,cast=.10),
  "hybrid: low genre":   dict(genres=.10, overview=.40, keywords=.30, director=.10, cast=.10),
  "hybrid: text-heavy":  dict(genres=.10, overview=.50, keywords=.30, director=.05, cast=.05),
  "ablation: genres":    dict(genres=1.0),
  "ablation: overview":  dict(overview=1.0),
  "ablation: keywords":  dict(keywords=1.0),
  "ablation: director":  dict(director=1.0),
  "ablation: cast":      dict(cast=1.0),
  "semantic only":     dict(semantic=1.0),
  "semantic + genre":  dict(semantic=.50, genres=.20, keywords=.15, director=.10, cast=.05),
  "semantic + kw":     dict(semantic=.60, keywords=.25, genres=.10, director=.05),
}

for name,w in WEIGHTS.items():
  runs[name]=lambda q,k,w=w:hybrid.recommend(q,k=k,weights=w)

print(f"\n{'model':26s} P@10 R@10")

for name, fn in runs.items():
    p, r = evaluate(fn)
    print(f"{name:26s} {p:.3f}  {r:.3f}")

# print(evaluate(tfidf.recommend,verbose=True)) 
# print(evaluate(emb.recommend,verbose=True)) 
# print(evaluate(hybrid.recommend,verbose=True))   

# BASE=dict(genres=.30,overview=.25,keywords=.20,director=.15,cast=.10)

# def with_genres(wg):
#   rest={f:v for f,v in BASE.items() if f!='genres'}
#   scale=(1-wg)/sum(rest.values())
#   return {"genres":wg,**{f:v*scale for f,v in rest.items()}} 
# print("genres analysis")
# for wg in [0.0,0.05,0.10,0.15,0.20,0.25,0.30]:
#   w=with_genres(wg)
#   p,r=evaluate(lambda q,k,w=w : hybrid.recommend(q,k,weights=w))
#   print(f"genre={wg:.2f}  P@10={p:.3f}  R@10={r:.3f}")

# BASE=dict(genres=.20,overview=.25,keywords=.20,director=.15,cast=.10)
# def with_overview(wg):
#   rest={f:v for f,v in BASE.items() if f!='overview'}
#   scale=(1-wg)/sum(rest.values())
#   return {"overview":wg,**{f:v*scale for f,v in rest.items()}} 
# print("overview analysis")
# for wg in [0.0,0.05,0.10,0.15,0.20,0.25,0.30]:
#   w=with_genres(wg)
#   p,r=evaluate(lambda q,k,w=w : hybrid.recommend(q,k,weights=w))
#   print(f"overview={wg:.2f}  P@10={p:.3f}  R@10={r:.3f}")
   
# w = dict(semantic=.60, keywords=.25, genres=.10, director=.05)
# for t in ["The Shawshank Redemption", "Titanic","Interstellar","Toy Story","The Dark Knight"]:
#     print(t); print(hybrid.recommend(t, weights=w).to_string())   

# from sklearn.metrics.pairwise import cosine_similarity
# i = hybrid._find("Titanic")
# print(hybrid.df.loc[i, "keywords"])
# print("nonzero keyword cells:", hybrid.blocks["keywords"][i].nnz)
# s = cosine_similarity(hybrid.blocks["keywords"][i:i + 1], hybrid.blocks["keywords"]).ravel()
# print("candidates with keyword score > 0:", (s > 0).sum(), "of", len(s))
# print("movies with no keywords:", round((hybrid.df["keywords"].str.len() == 0).mean(), 3))
# print(hybrid.recommend("Titanic", weights=dict(keywords=1.0)).head(10).to_string())