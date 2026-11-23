from pathlib import Path
import numpy as np
from recomai.movies.engine import ContentRecommender

class EmbeddingRecommender(ContentRecommender):
    def __init__(self, config, model_name="all-MiniLM-L6-v2", cache_dir="cache"):
        super().__init__(config)
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)

    def _text(self, row):
        # readable text; main description first because the model truncates long input
        parts = [str(row[f]) for f in self.config.text_fields]
        for f in self.config.list_fields:
            if row[f]:
                parts.append(f"{f}: {', '.join(row[f])}.")
        return " ".join(parts)

    def _vectorize(self):
        cache = self.cache_dir / f"{self.config.name}_{self.model_name}.npy"
        if cache.exists():
            emb = np.load(cache)
            if emb.shape[0] == len(self.df):      # ignore a stale cache
                return emb

        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(self.model_name)
        texts = self.df.apply(self._text, axis=1).tolist()
        emb = model.encode(texts, batch_size=64, show_progress_bar=True,
                           normalize_embeddings=True)
        self.cache_dir.mkdir(exist_ok=True)
        np.save(cache, emb)
        return emb