from recomai.books.config import BOOK_CONFIG, BookConfig
from recomai.books.engine import CollaborativeBookRecommender
from recomai.books.loader.books import build_pivot_table, load_books
from recomai.domains.base import DomainRecommender


class BookDomain(DomainRecommender):
    """Books: item-item collaborative filtering. Loads and fits in __init__, like MovieDomain."""

    name = "books"
    label = "Books"
    supports_diversity = False       # collaborative filtering has no diversity step
    default_diversity = 0.0

    def __init__(self, data_dir="data", config: BookConfig = BOOK_CONFIG):
        self.config = config
        books, ratings = load_books(data_dir)
        pt = build_pivot_table(books, ratings,
                               min_book_ratings=config.min_book_ratings,
                               min_user_ratings=config.min_user_ratings)
        self._engine = CollaborativeBookRecommender(config).fit(books, pt)

    def search(self, query, limit=5):
        return self._engine.search(query, limit=limit)

    def recommend(self, item_id, k=10, filters=None, diversity=0.0):
        return self._engine.recommend(item_id, k=k, filters=filters)   # diversity is ignored

    def filter_schema(self):
        return self._engine.filter_schema()