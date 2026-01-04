import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .models.condition import AreaName, StatusType, TrailCondition

logger = logging.getLogger(__name__)


def condition_list(request):
    queryset = TrailCondition.objects.filter(disabled=False)

    # フィルタリング（既存通り）
    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(Q(trail_name__icontains=search_query) | Q(mountain_name_raw__icontains=search_query))

    status_filter = request.GET.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    area_filter = request.GET.get("area")
    if area_filter:
        queryset = queryset.filter(area=area_filter)

    # デフォルトを更新日時に変更
    sort_key = request.GET.get("sort", "-updated_at")
    queryset = queryset.order_by(sort_key)

    return render(
        request,
        "index.html",
        {
            "conditions": queryset,
            "status_choices": StatusType.choices,
            "area_choices": AreaName.choices,
            "current_sort": sort_key,  # 現在のソートキーをテンプレートに渡す
        },
    )


# trail_status/views.py


def condition_detail(request, pk):
    item = get_object_or_404(TrailCondition, pk=pk)
    return render(request, "detail.html", {"item": item})
