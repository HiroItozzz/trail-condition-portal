from rest_framework import serializers
from trail_status.models.condition import TrailCondition
from trail_status.models.source import DataSource

class TrailConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrailCondition
        fields = "__all__"