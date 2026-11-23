from dataclasses import dataclass, field

@dataclass(frozen=True)
class DomainConfig:
    name: str
    title_col: str = "title"
    text_fields: tuple = ()   # free text: overview, description, lyrics
    list_fields: tuple = ()   # entity lists: genres, cast, authors...
    tfidf_params: dict = field(default_factory=dict)
    weights: dict=field(default_factory=dict)
    profiles: dict=field(default_factory=dict)
    reason_labels:dict=field(default_factory=dict)

MOVIE_CONFIG = DomainConfig(
    name="movies",
    text_fields=("overview",),
    list_fields=("genres", "keywords", "cast", "director"),
    tfidf_params=dict(stop_words="english", ngram_range=(1, 1),
                      min_df=2, max_df=0.8),
    weights=dict(semantic=.50, genres=.20, keywords=.15, director=.10, cast=.05),
    profiles={
    "keyword_heavy": dict(semantic=.60, keywords=.25, genres=.10, director=.05),
    },
    reason_labels={
        "genres":"Shares genres",
        "Keywords":"Shares keywords",
        "Director":"Shares director",
        "Cast":"Shares cast",
    }
)