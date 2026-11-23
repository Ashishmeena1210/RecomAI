from recomai.movies.config import MOVIE_CONFIG
from recomai.movies.loader.movies import load_movies
from recomai.movies.engine import ContentRecommender

# Load movie dataset
df = load_movies("data")

# Train recommendation engine
rec = ContentRecommender(MOVIE_CONFIG).fit(df)

# Generate recommendations
print(rec.recommend("The Shawshank Redemption"))
print(rec.recommend("Avengers: Age of Ultron"))
print(rec.recommend("Titanic"))
print(rec.recommend("Harry Potter and the Order of the Phoenix"))
