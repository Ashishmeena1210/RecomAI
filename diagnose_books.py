import pandas as pd
from pathlib import Path

base = Path("data/books")

print("=== FILES IN data/books/ ===")
print(list(base.iterdir()))

books   = pd.read_csv(base / "Books.csv",   encoding="latin-1", low_memory=False)
ratings = pd.read_csv(base / "Ratings.csv", encoding="latin-1")

books.columns   = [c.strip() for c in books.columns]
ratings.columns = [c.strip() for c in ratings.columns]

print("\n=== COLUMN NAMES ===")
print("Books  :", books.columns.tolist())
print("Ratings:", ratings.columns.tolist())

print("\n=== RAW SHAPES ===")
print("Books  :", books.shape)
print("Ratings:", ratings.shape)

user_col   = ratings.columns[0]
isbn_col   = ratings.columns[1]
rating_col = ratings.columns[2]

print("\n=== RATING VALUE DISTRIBUTION ===")
print(ratings[rating_col].value_counts().sort_index())

explicit = ratings[ratings[rating_col] > 0].copy()
print(f"\nExplicit ratings (>0): {len(explicit):,}")
print(f"Zero ratings          : {len(ratings) - len(explicit):,}")

print("\n=== TOP-10 MOST ACTIVE USERS (explicit ratings) ===")
user_counts = explicit.groupby(user_col)[rating_col].count().sort_values(ascending=False)
print(user_counts.head(10))

print("\n=== TOP-10 MOST RATED BOOKS (after merging titles) ===")
merged = explicit.merge(books[["ISBN", "Book-Title"]], left_on=isbn_col, right_on="ISBN", how="left")
book_counts = merged.groupby("Book-Title")[rating_col].count().sort_values(ascending=False)
print(book_counts.head(10))

print("\n=== THRESHOLD ANALYSIS (how many books survive each combo) ===")
print(f"{'min_user':>10} {'min_book':>10} {'users':>8} {'books':>8}")
for min_u in [50, 100, 200]:
    active_ids = user_counts[user_counts >= min_u].index
    sub = explicit[explicit[user_col].isin(active_ids)]
    sub = sub.merge(books[["ISBN", "Book-Title"]], left_on=isbn_col, right_on="ISBN", how="left").dropna(subset=["Book-Title"])
    bc = sub.groupby("Book-Title")[rating_col].count()
    for min_b in [10, 25, 50]:
        pop = bc[bc >= min_b]
        print(f"{min_u:>10} {min_b:>10} {len(active_ids):>8} {len(pop):>8}")

print("\n=== RECOMMENDED THRESHOLDS ===")
# Find thresholds that give roughly the original 706 books
for min_u in [50, 100, 200]:
    active_ids = user_counts[user_counts >= min_u].index
    sub = explicit[explicit[user_col].isin(active_ids)]
    sub = sub.merge(books[["ISBN", "Book-Title"]], left_on=isbn_col, right_on="ISBN", how="left").dropna(subset=["Book-Title"])
    bc = sub.groupby("Book-Title")[rating_col].count()
    for min_b in [10, 25, 50]:
        pop = bc[bc >= min_b]
        if 500 <= len(pop) <= 1000:
            print(f"  min_user_ratings={min_u}, min_book_ratings={min_b}  → {len(pop)} books (GOOD)")
