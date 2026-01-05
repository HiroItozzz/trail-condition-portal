import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .models.condition import AreaName, StatusType, TrailCondition

logger = logging.getLogger(__name__)


def trail_list(request):
    conditions = TrailCondition.objects.filter(disabled=False)

    # クエリパラメータによる絞り込み
    area_filter = request.GET.get("area")
    status_filter = request.GET.get("status")

    if area_filter:
        conditions = conditions.filter(area=area_filter)
    if status_filter:
        conditions = conditions.filter(status=status_filter)

    # 更新日時（updated_at）の降順で並べ替え
    conditions = conditions.order_by("-updated_at")

    context = {
        "conditions": conditions,
        "area_choices": AreaName.choices,
        "status_choices": StatusType.choices,
        "current_area": area_filter,
        "current_status": status_filter,
    }
    return render(request, "trail_list.html", context)


# trail_status/views.py


def condition_detail(request, pk):
    item = get_object_or_404(TrailCondition, pk=pk)
    return render(request, "detail.html", {"item": item})
