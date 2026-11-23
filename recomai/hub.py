from recomai.domains.base import DomainRecommender


class RecomAIHub:
    """
    Single entry-point that routes search / recommend / filter_schema
    calls to the correct domain engine by name.
    """

    def __init__(self):
        self._engines: dict[str, DomainRecommender] = {}

    def register(self, engine: DomainRecommender) -> "RecomAIHub":
        """Register a domain engine. Uses engine.name as the key."""
        if not isinstance(engine, DomainRecommender):
            raise TypeError(f"{engine!r} must subclass DomainRecommender")
        self._engines[engine.name] = engine
        return self

    def search(self, domain: str, query: str, limit: int = 5) -> list[dict]:
        return self._get(domain).search(query, limit=limit)

    def recommend(self, domain: str, item_id: str,
                  k: int = 10, filters: dict | None = None,
                  diversity: float = 0.0) -> list[dict]:
        return self._get(domain).recommend(item_id, k=k,
                                           filters=filters,
                                           diversity=diversity)

    def filter_schema(self, domain: str) -> list[dict]:
        return self._get(domain).filter_schema()

    def supports_diversity(self, domain: str) -> bool:
        return self._get(domain).supports_diversity

    def domains(self) -> list[str]:
        return list(self._engines.keys())

    def _get(self, domain: str) -> DomainRecommender:
        if domain not in self._engines:
            raise KeyError(
                f"Domain '{domain}' not registered. "
                f"Available: {self.domains()}"
            )
        return self._engines[domain]