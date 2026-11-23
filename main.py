from recomai.config import MOVIE_CONFIG
from recomai.loaders.movies import load_movies
from recomai.engine import ContentRecommender

df = load_movies("data")
rec = ContentRecommender(MOVIE_CONFIG).fit(df)

print(rec.recommend("The Shawshank Redemption"))
print(rec.recommend("Avengers: Age of Ultron"))
print(rec.recommend("Titanic"))
print(rec.recommend("Harry Potter and the Order of the Phoenix"))

