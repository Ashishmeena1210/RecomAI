from pathlib import Path

import numpy as np
import pandas as pd

from recomai.songs.config import SONG_CONFIG, SongConfig


def load_songs(data_dir="data", config: SongConfig = SONG_CONFIG) -> pd.DataFrame:
    """Load and clean <data_dir>/songs/<config.csv_name>. One row per distinct track.

    Cleaning follows the notebook, with three deliberate differences (marked below).
    The number of rows dropped by each step is saved in df.attrs["dropped"].
    """
    c = config
    path = Path(data_dir) / "songs" / c.csv_name
    df = pd.read_csv(path, low_memory=False)
    df.columns = [col.strip() for col in df.columns]

    features = list(c.features)
    required = [c.id_col, c.title_col, c.artist_col, c.genre_col, c.popularity_col] + features
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns {missing}; found {list(df.columns)}")
    for col, default in [(c.album_col, ""), (c.explicit_col, False), (c.duration_col, np.nan)]:
        if col not in df.columns:
            df[col] = default

    dropped = {"start": len(df)}
    # "Unnamed: 0" is the saved row number; it made the notebook's first drop_duplicates() a no-op
    df = df.drop(columns=[col for col in df.columns if col.startswith("Unnamed")])
    df[c.title_col] = df[c.title_col].fillna("").astype(str).str.strip()
    df[c.artist_col] = df[c.artist_col].fillna("").astype(str).str.strip()
    df[c.popularity_col] = pd.to_numeric(df[c.popularity_col], errors="coerce")

    before = len(df)
    df = df[df[c.title_col] != ""]
    df = df.dropna(subset=[c.id_col, c.genre_col, c.popularity_col] + features)
    dropped["empty name / missing values"] = before - len(df)
    df[c.id_col] = df[c.id_col].astype(str).str.strip()

    # DIFFERENCE 1: the file lists one track once per genre (about a fifth of the rows), and the
    # notebook kept an arbitrary one. Keep ALL of a track's genres, so genre matching and the genre
    # filter see every genre the track is listed under.
    genre_map = (df.groupby([c.title_col, c.artist_col])[c.genre_col]
                   .agg(lambda s: sorted(set(s))).to_dict())

    # DIFFERENCE 2: most popular listing first, so every drop below keeps the most popular copy
    # (the notebook kept whichever copy came first in the file)
    df = df.sort_values(c.popularity_col, ascending=False, kind="stable")

    for label, subset in [
        ("same track_id in several genres", [c.id_col]),
        ("same name + artists (the notebook's rule)", [c.title_col, c.artist_col]),
        # DIFFERENCE 3: identical audio on all features = the same recording listed under another
        # title or album ('Kesariya' vs 'Kesariya (From "Brahmastra")' scored distance 0 in the notebook)
        ("identical audio features (same recording)", features),
    ]:
        before = len(df)
        df = df.drop_duplicates(subset=subset)
        dropped[label] = before - len(df)

    df = df.reset_index(drop=True)
    df["genres"] = [genre_map[(t, a)] for t, a in zip(df[c.title_col], df[c.artist_col])]
    dropped["final"] = len(df)
    df.attrs["dropped"] = dropped
    return df
