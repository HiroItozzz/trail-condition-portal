from rest_framework import serializers

from trail_status.models import DataSource, TrailCondition


class TrailConditionSerializer(serializers.ModelSerializer):
    # get_area_display というDjango標準のメソッドを利用して日本語名を取得
    area_display = serializers.CharField(source="get_area_display", read_only=True)

    class Meta:
        model = TrailCondition
        fields = "__all__"
