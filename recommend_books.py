from recomai.domains.books import build_book_domain
from recomai.hub import RecomAIHub

hub=RecomAIHub()
hub.register(build_book_domain(data_dir="data"))

BOOK_TITLES=['Animal Farn',]
hits=[]
for b in BOOK_TITLES:
  hits=hub.search('books',b,limit=3)
  print(hits)
  print("\n")
  print("recommendation")
  id=hits[0]["id"]
  print(hub.recommend('books',id,k=3))


