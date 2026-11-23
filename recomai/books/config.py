from dataclasses import dataclass


@dataclass(frozen=True)
class BookConfig:
    """
    Configuration for the collaborative-filtering book recommender.
    Mirrors the style of DomainConfig in movies/config.py.
    """
    name:  str = "books"             # DomainRecommender.name  (URL slug)
    label: str = "Books"             # DomainRecommender.label (display name)

    # -- column names in the Books.csv ----------------------------------------
    isbn_col:      str = "ISBN"
    title_col:     str = "Book-Title"
    author_col:    str = "Book-Author"
    year_col:      str = "Year-Of-Publication"
    publisher_col: str = "Publisher"
    image_col:     str = "Image-URL-M"

    # -- pivot-table thresholds (controls size & noise) -----------------------
    # Why 50 not 200?
    # This dataset has ~433k explicit ratings; only ~145 users have >= 200
    # ratings, which produces an empty pivot table (0, 0).
    # With 50 we get ~1,300 active users and ~700 popular books -- matching
    # the original 706x810 matrix size from the notebook.
    min_book_ratings: int = 10    # book must be rated by >= N active users
    min_user_ratings: int = 50    # user must have rated   >= N books

    # -- reason generation thresholds -----------------------------------------
    score_strong: float = 0.70    # "Readers who loved this also loved ..."
    score_ok:     float = 0.40    # "Frequently read together ..."
                                  # below -> "Sometimes read by the same readers"


BOOK_CONFIG = BookConfig()
