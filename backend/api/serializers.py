from rest_framework import serializers


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=1, max_length=200, trim_whitespace=True)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=5)


class RecommendRequestSerializer(serializers.Serializer):
    item_id = serializers.CharField(max_length=200)          # ids are str in your contract
    k = serializers.IntegerField(min_value=1, max_value=50, default=10)
    diversity = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.0)
    filters = serializers.DictField(required=False, allow_null=True)