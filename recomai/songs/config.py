from dataclasses import dataclass


@dataclass(frozen=True)
class SongConfig:
    """Configuration for the audio-feature song recommender (from the songs notebook)."""
    name:  str = "songs"             # DomainRecommender.name  (URL slug)
    label: str = "Songs"             # DomainRecommender.label (display name)
    csv_name: str = "spotify.csv"    # expected at <data_dir>/songs/spotify.csv

    # -- column names in spotify.csv -------------------------------------------
    id_col:         str = "track_id"
    title_col:      str = "track_name"
    artist_col:     str = "artists"          # several artists are separated by ";"
    album_col:      str = "album_name"
    genre_col:      str = "track_genre"
    popularity_col: str = "popularity"
    explicit_col:   str = "explicit"
    duration_col:   str = "duration_ms"

    # -- audio features used for similarity (the notebook's final list of 9) ----
    features: tuple = ("valence", "danceability", "energy", "tempo", "acousticness",
                       "liveness", "speechiness", "instrumentalness", "loudness")

    # -- ranking: score = w_audio*cosine + w_genre*same genre + w_artist*shared artist
    # The 0.70 / 0.20 / 0.10 weights come from the notebook. Like the movie weights, they are
    # untested guesses: keep them here so they can be evaluated and changed.
    w_audio:  float = 0.70
    w_genre:  float = 0.20
    w_artist: float = 0.10
    pool:     int = 100       # nearest tracks by audio considered before the genre/artist bonus

    # a "sounds alike" reason is shown for a trait only if BOTH tracks are at least this many
    # standard deviations from the dataset average, in the same direction ...
    trait_z: float = 0.5
    # ... AND the trait is distinctive: at most this share of ALL tracks lies that far on that side
    # (otherwise nearly every track is "vocal" or "not live-sounding" and the reason says nothing)
    trait_max_share: float = 0.35

    # do not recommend other versions of the same song (same title apart from "(From ...)", "- Reprise",
    # "- Remastered" ... AND at least one shared artist). Covers by other artists are kept.
    exclude_versions: bool = True


SONG_CONFIG = SongConfig()
