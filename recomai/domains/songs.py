from recomai.domains.base import DomainRecommender
from recomai.songs.config import SONG_CONFIG, SongConfig
from recomai.songs.engine import AudioSongRecommender
from recomai.songs.loaders.songs import load_songs


class SongDomain(DomainRecommender):
    """Songs: cosine similarity on audio features + genre / shared-artist bonus.
    Loads and fits in __init__, like MovieDomain and BookDomain."""

    name = "songs"
    label = "Songs"
    supports_diversity = True
    default_diversity = 0.0          # not validated for songs yet

    def __init__(self, data_dir="data", config: SongConfig = SONG_CONFIG):
        self.config = config
        self._engine = AudioSongRecommender(config).fit(load_songs(data_dir, config))

    def search(self, query, limit=5):
        return self._engine.search(query, limit=limit)

    def recommend(self, item_id, k=10, filters=None, diversity=0.0):
        return self._engine.recommend(item_id, k=k, filters=filters, diversity=diversity)

    def filter_schema(self):
        return self._engine.filter_schema()
