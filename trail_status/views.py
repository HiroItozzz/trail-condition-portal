import logging
from datetime import timedelta

from django.db.models import Max, Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models.condition import AreaName, DataSource, StatusType, TrailCondition

logger = logging.getLogger(__name__)


def trail_list(request: HttpRequest) -> HttpResponse:
    conditions = TrailCondition.objects.filter(disabled=False)

    # クエリパラメータによる絞り込み
    source_filter = request.GET.get("source")
    area_filter = request.GET.get("area")
    status_filter = request.GET.get("status")

    if source_filter:
        conditions = conditions.filter(source=source_filter)
    if area_filter:
        conditions = conditions.filter(area=area_filter)
    if status_filter:
        conditions = conditions.filter(status=status_filter)

    # 更新日時（updated_at）の降順で並べ替え
    conditions = conditions.order_by("-updated_at")
    updated_sources = (
        TrailCondition.objects.values("source__name", "source__url1")
        .annotate(latest_date=Max("updated_at"))
        .order_by("-latest_date")
    )
    latest_checked_at = DataSource.objects.aggregate(Max("last_scraped_at"))["last_scraped_at__max"]

    seven_days_ago = timezone.now().date() - timedelta(days=7)

    # 各カテゴリの件数をカウント
    base_conditions = TrailCondition.objects.filter(disabled=False)
    
    # 山域別の件数
    area_counts = dict(base_conditions.values('area').annotate(count=Count('id')).values_list('area', 'count'))
    area_choices_with_count = [(id, name) for id, name in AreaName.choices if area_counts.get(id, 0) > 0]
    
    # 状況別の件数
    status_counts = dict(base_conditions.values('status').annotate(count=Count('id')).values_list('status', 'count'))
    status_choices_with_count = [(id, name) for id, name in StatusType.choices if status_counts.get(id, 0) > 0]
    
    # サイト別の件数（DataSourceは別途取得）
    source_counts = dict(base_conditions.values('source').annotate(count=Count('id')).values_list('source', 'count'))
    source_choices_with_count = [(id, name) for id, name in DataSource.objects.get_choices() if source_counts.get(id, 0) > 0]

    context = {
        "conditions": conditions,
        "source_choices": source_choices_with_count,
        "area_choices": area_choices_with_count,
        "status_choices": status_choices_with_count,
        "current_source": source_filter,
        "current_area": area_filter,
        "current_status": status_filter,
        "updated_sources": updated_sources,
        "latest_checked_at": latest_checked_at,
        "seven_days_ago": seven_days_ago,
    }
    return render(request, "trail_list.html", context)


# trail_status/views.py


def condition_detail(request: HttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(TrailCondition, pk=pk)
    return render(request, "detail.html", {"item": item})
