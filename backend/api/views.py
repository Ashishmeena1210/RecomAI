from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .hub_registry import get_hub
from .serializers import RecommendRequestSerializer, SearchQuerySerializer
from .utils import jsonable


def _resolve(domain: str):
    hub = get_hub()
    if domain not in hub.domains():
        raise NotFound(f"Unknown domain '{domain}'. Available: {hub.domains()}")
    return hub, hub._get(domain)      # tip: add a public `engine(name)` to RecomAIHub later


def _describe(engine) -> dict:
    return {
        "name": engine.name,
        "label": engine.label,
        "supports_diversity": engine.supports_diversity,
        "default_diversity": engine.default_diversity,
    }


@api_view(["GET"])
def health(request):
    # Deliberately does NOT touch the hub, so it answers while models still load.
    return Response({"status": "ok"})


class DomainListView(APIView):
    def get(self, request):
        hub = get_hub()
        return Response({"domains": [_describe(hub._get(n)) for n in hub.domains()]})


class SchemaView(APIView):
    def get(self, request, domain):
        hub, engine = _resolve(domain)
        return Response({**_describe(engine), "filters": jsonable(engine.filter_schema())})


class SearchView(APIView):
    def get(self, request, domain):
        hub, _ = _resolve(domain)
        s = SearchQuerySerializer(data=request.query_params)
        s.is_valid(raise_exception=True)
        q, limit = s.validated_data["q"], s.validated_data["limit"]
        results = hub.search(domain, q, limit=limit)
        return Response({"domain": domain, "query": q, "results": jsonable(results)})


class RecommendView(APIView):
    def post(self, request, domain):
        hub, engine = _resolve(domain)
        s = RecommendRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        filters = d.get("filters") or None
        if filters:
            allowed = {f["key"] for f in engine.filter_schema()}
            unknown = sorted(set(filters) - allowed)
            if unknown:
                raise ValidationError({"filters": f"Unknown filter(s) {unknown}. Allowed: {sorted(allowed)}"})

        diversity = d["diversity"] if engine.supports_diversity else 0.0

        try:
            results = hub.recommend(domain, d["item_id"], k=d["k"],
                                    filters=filters, diversity=diversity)
        except KeyError:
            raise NotFound(f"Item '{d['item_id']}' not found in '{domain}'.")

        return Response({
            "domain": domain,
            "item_id": d["item_id"],
            "k": d["k"],
            "diversity_applied": diversity,
            "count": len(results),
            "results": jsonable(results),
        })