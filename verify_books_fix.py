"""
Quick smoke-test for the books loader fix.
Run from project root:  <venv>/Scripts/python.exe verify_books_fix.py
"""
import sys
sys.path.insert(0, ".")

from recomai.loaders.books import load_books, build_pivot_table
from recomai.books.config import BOOK_CONFIG

print("Loading CSVs...")
books, users, ratings = load_books("data")
print(f"  Books   : {books.shape}")
print(f"  Ratings : {ratings.shape}  (explicit only)")

print(f"\nBuilding pivot table (min_user={BOOK_CONFIG.min_user_ratings}, min_book={BOOK_CONFIG.min_book_ratings})...")
pt = build_pivot_table(
    books, users, ratings,
    min_book_ratings=BOOK_CONFIG.min_book_ratings,
    min_user_ratings=BOOK_CONFIG.min_user_ratings,
)
print(f"  Pivot table shape: {pt.shape}  (books x users)")

assert pt.shape[0] > 0, "Still empty! Thresholds still too high."
assert pt.shape[1] > 0, "No users survived the filter."
print(f"\n  Sample book titles:")
for t in pt.index[:5]:
    print(f"    {t}")

print("\nFix confirmed. cosine_similarity will work now.")
