from pathlib import Path

import pandas as pd

USER, ISBN, RATING = "User-ID", "ISBN", "Book-Rating"
TITLE, AUTHOR = "Book-Title", "Book-Author"
BOOK_COLUMNS = [ISBN, TITLE, AUTHOR, "Year-Of-Publication", "Publisher", "Image-URL-M"]


def _read(path, **kw):
    """UTF-8 first; fall back to latin-1 only if the file is not valid UTF-8."""
    try:
        return pd.read_csv(path, encoding="utf-8", **kw)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kw)


def _require(df, columns, name):
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing columns {missing}; found {list(df.columns)}")


def load_books(data_dir="data"):
    """Load Books.csv and Ratings.csv from <data_dir>/books/. Users.csv is not needed.

    The file names must match exactly (Linux is case-sensitive, which matters when you deploy).
    Returns (books, ratings): books has one row per ISBN; ratings holds explicit ratings only.
    """
    base = Path(data_dir) / "books"
    books = _read(base / "Books.csv", dtype={ISBN: str}, low_memory=False)
    ratings = _read(base / "Ratings.csv", dtype={ISBN: str})
    books.columns = [c.strip() for c in books.columns]
    ratings.columns = [c.strip() for c in ratings.columns]
    _require(books, BOOK_COLUMNS, "Books.csv")
    _require(ratings, [USER, ISBN, RATING], "Ratings.csv")

    books[ISBN] = books[ISBN].astype(str).str.strip()
    ratings[ISBN] = ratings[ISBN].astype(str).str.strip()
    books = (books.dropna(subset=[TITLE, AUTHOR])
                  .drop_duplicates(ISBN)             # a repeated ISBN would multiply its ratings
                  .reset_index(drop=True))
    ratings = ratings[ratings[RATING] > 0].copy()   # 0 = "read but not rated" in Book-Crossing
    return books, ratings


def build_pivot_table(books, ratings, min_book_ratings=10, min_user_ratings=50):
    """Book-Title x User-ID matrix of explicit ratings (0 = not rated).

    Thresholds count EXPLICIT ratings only, unlike the original notebook, which counted all
    1.1M rows including the zeros. That is why the notebook's 200 does not carry over.
      min_user_ratings: a user needs at least this many explicit ratings to count as active
      min_book_ratings: a book needs ratings from at least this many active users
    """
    per_user = ratings.groupby(USER).size()
    active = per_user[per_user >= min_user_ratings].index
    filtered = ratings[ratings[USER].isin(active)]
    if filtered.empty:
        raise RuntimeError(
            f"No users have >= {min_user_ratings} explicit ratings (max is {per_user.max()}). "
            f"Lower min_user_ratings (try {max(1, int(per_user.max() // 4))}).")

    filtered = filtered.merge(books[[ISBN, TITLE]], on=ISBN, how="inner")
    per_book = filtered.groupby(TITLE)[USER].nunique()       # distinct active users per book
    popular = per_book[per_book >= min_book_ratings].index
    filtered = filtered[filtered[TITLE].isin(popular)]
    if filtered.empty:
        raise RuntimeError(
            f"No books are rated by >= {min_book_ratings} active users (max is {per_book.max()}). "
            f"Lower min_book_ratings (try {max(1, int(per_book.max() // 4))}).")

    return (filtered.pivot_table(index=TITLE, columns=USER, values=RATING, aggfunc="mean")
                    .fillna(0))