import logging
from datetime import timedelta

from django.views.generic import ListView, DetailView
from django.db.models import Count, F, Max
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import AreaName, BlogFeed, DataSource, StatusType, TrailCondition
import urllib.parse

from django.db.models import Prefetch
from collections import OrderedDict

logger = logging.getLogger(__name__)


class SideBarMixin:
    """サイドバー用のフィルター選択肢を取得（データがある項目のみ表示）"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(**_get_sidebar_context())
        return context


class SourceListView(SideBarMixin, ListView):
    """情報源一覧ページ"""
    model = DataSource
    query_set = DataSource.objects.filter(data_format="WEB").order_by("organization_type", "id")
    template_name = "sources.html"
    context_object_name = "sources"


class BlogListView(SideBarMixin, ListView):
    """巡視ブログ一覧ページ"""
    model = DataSource
    template_name = "blogs.html"

    def get_queryset(self):
        # @formatter:off
        query_set = (DataSource.objects.filter(data_format="BLOG")
                     .prefetch_related(
            Prefetch(
                "blogfeed_set",
                queryset=BlogFeed.objects.filter(disabled=False).order_by("-published_at")[:4],
                to_attr="recent_feeds",
            )
        ).order_by("area_name", "id")
                     )
        # @formatter:on
        return query_set

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # エリア別にグルーピング（AreaName.choices の順序を維持）
        area_order = [code for code, _ in AreaName.choices]
        area_labels = dict(AreaName.choices)

        grouped = OrderedDict()
        for source in self.object_list:
            area_code = source.area_name or "OTHER"
            if area_code not in grouped:
                grouped[area_code] = {
                    "label": area_labels.get(area_code, "その他"),
                    "sources": [],
                }
            grouped[area_code]["sources"].append(source)

        # AreaName.choices の順序でソート（OTHER は末尾）
        sorted_grouped = OrderedDict()
        for code in area_order:
            if code in grouped:
                sorted_grouped[code] = grouped[code]
        if "OTHER" in grouped:
            sorted_grouped["OTHER"] = grouped["OTHER"]

        context["grouped_sources"] = sorted_grouped
        return context


def _get_sidebar_context() -> dict:
    """サイドバー用のフィルター選択肢を取得（データがある項目のみ表示）"""
    base_conditions = TrailCondition.objects.filter(disabled=False)

    # 最近追加された情報源（1週間以内、最新5件）
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_sources = (
        DataSource.objects.filter(data_format="WEB", created_at__gte=seven_days_ago)
        .order_by("-created_at")[:5]
        .values("id", "name", "created_at")
    )

    # 山域フィルター選択肢（データがある山域のみ）
    area_counts = dict(base_conditions.values("area").annotate(count=Count("id")).values_list("area", "count"))
    area_choices = [(id, name) for id, name in AreaName.choices if area_counts.get(id, 0) > 0]

    # 状況フィルター選択肢（データがある状況タイプのみ）
    status_counts = dict(base_conditions.values("status").annotate(count=Count("id")).values_list("status", "count"))
    status_choices = [(id, name) for id, name in StatusType.choices if status_counts.get(id, 0) > 0]

    # 情報源フィルター選択肢（データがある情報源のみ）
    source_counts = dict(base_conditions.values("source").annotate(count=Count("id")).values_list("source", "count"))
    source_choices = [
        (id, name)
        for id, name in DataSource.objects.filter(data_format="WEB").get_choices()
        if source_counts.get(id, 0) > 0
    ]

    return {
        "source_choices": source_choices,
        "area_choices": area_choices,
        "status_choices": status_choices,
        "recent_sources": list(recent_sources),
    }


class TrailDetailView(SideBarMixin, DetailView):
    model = TrailCondition
    template_name = "detail.html"
    context_object_name = "item"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)


        # ヤマレコ検索リンク生成
        yamareco_base_url = "https://www.yamareco.com/modules/yamareco/search_record.php"
        yamareco_fixed_params = {'isphoto': 1, 'request': 1, 'submit': 'submit'}

        yamareco_area_id = AreaName.get_yamareco_area_id(self.object.area)
        params = {
            'place': self.object.mountain_name_raw,
            'area': yamareco_area_id,
            **yamareco_fixed_params,
        }
        context["yamareco_url"] = f"{yamareco_base_url}?{urllib.parse.urlencode(params, encoding='euc-jp')}"

        return context

def trail_list(request: HttpRequest) -> HttpResponse:
    base_conditions = TrailCondition.objects.filter(disabled=False).prefetch_related("source")
    base_datasources = DataSource.objects.filter(data_format="WEB")

    # クエリパラメータによる絞り込み
    source_filter = request.GET.get("source")
    area_filter = request.GET.get("area")
    status_filter = request.GET.get("status")

    conditions = base_conditions
    if source_filter:
        conditions = conditions.filter(source=source_filter)
    if area_filter:
        conditions = conditions.filter(area=area_filter)
    if status_filter:
        conditions = conditions.filter(status=status_filter)

    # 報告日の降順で並べ替え（updated_atは表示用のみ）
    conditions = conditions.order_by("-reported_at", "-created_at")

    # 最新の内容更新日（全情報源含む）
    latest_update_date = TrailCondition.objects.filter(source__isnull=False).aggregate(Max("updated_at"))[
        "updated_at__max"
    ]

    # 1週間以内の更新リスト（新規追加情報源は除外）
    # 新規追加情報源 = DataSource.created_atとTrailCondition.updated_atの差が1日以内
    updated_sources_query = (
        TrailCondition.objects.filter(source__isnull=False)
        .values("source__name", "source__url1")
        .annotate(
            latest_date=Max("updated_at"),
            source_created_at=F("source__created_at"),
        )
        .order_by("-latest_date")
    )
    # DataSourceの作成日とTrailConditionの最新更新日の差が1日以内のものを除外
    updated_sources = [
        item for item in updated_sources_query if item["latest_date"] - item["source_created_at"] > timedelta(days=1)
    ]

    last_checked_at = base_datasources.aggregate(Max("last_checked_at"))["last_checked_at__max"]
    seven_days_ago = timezone.now().date() - timedelta(days=7)

    context = {
        "conditions": conditions,
        "current_source": source_filter,
        "current_area": area_filter,
        "current_status": status_filter,
        "latest_update_date": latest_update_date,
        "updated_sources": updated_sources,
        "last_checked_at": last_checked_at,
        "seven_days_ago": seven_days_ago,
        **_get_sidebar_context(),
    }
    return render(request, "trail_list.html", context)

