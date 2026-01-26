import logging
from datetime import timedelta

from django.db.models import Count, Max
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic.base import RedirectView

from .models.condition import AreaName, DataSource, StatusType, TrailCondition

logger = logging.getLogger(__name__)


class ArticleCounterRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = "condition-detail"

    def get_redirect_url(self, *args, **kwargs):
        return super().get_redirect_url(*args, **kwargs)


def _get_sidebar_context() -> dict:
    """サイドバー用のフィルター選択肢を取得"""
    base_conditions = TrailCondition.objects.filter(disabled=False)

    # 山域別の件数
    area_counts = dict(base_conditions.values("area").annotate(count=Count("id")).values_list("area", "count"))
    area_choices = [(id, name) for id, name in AreaName.choices if area_counts.get(id, 0) > 0]

    # 状況別の件数
    status_counts = dict(base_conditions.values("status").annotate(count=Count("id")).values_list("status", "count"))
    status_choices = [(id, name) for id, name in StatusType.choices if status_counts.get(id, 0) > 0]

    # サイト別の件数
    source_counts = dict(base_conditions.values("source").annotate(count=Count("id")).values_list("source", "count"))
    source_choices = [(id, name) for id, name in DataSource.objects.get_choices() if source_counts.get(id, 0) > 0]

    # 最近追加された情報源（1週間以内、最新5件）
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_sources = (
        DataSource.objects.filter(created_at__gte=seven_days_ago)
        .order_by("-created_at")[:5]
        .values("id", "name", "created_at")
    )

    return {
        "source_choices": source_choices,
        "area_choices": area_choices,
        "status_choices": status_choices,
        "recent_sources": list(recent_sources),
    }


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
    last_checked_at = DataSource.objects.aggregate(Max("last_checked_at"))["last_checked_at__max"]

    seven_days_ago = timezone.now().date() - timedelta(days=7)

    context = {
        "conditions": conditions,
        "current_source": source_filter,
        "current_area": area_filter,
        "current_status": status_filter,
        "updated_sources": updated_sources,
        "last_checked_at": last_checked_at,
        "seven_days_ago": seven_days_ago,
        **_get_sidebar_context(),
    }
    return render(request, "trail_list.html", context)


def trail_detail(request: HttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(TrailCondition, pk=pk)
    context = {"item": item, **_get_sidebar_context()}
    return render(request, "detail.html", context=context)

# クエリパラメータからパスパラメータへのリダイレクト
def trail_redirect(request: HttpRequest) -> HttpResponseRedirect:
    trail_id = request.GET.get("id")
    if trail_id:
        return redirect("trail-detail", pk=trail_id)
    return redirect("trail-list")


