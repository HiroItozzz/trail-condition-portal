import logging
import urllib.parse
from collections import OrderedDict, defaultdict
from datetime import timedelta
from typing import override

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Max, Prefetch
from django.forms import model_to_dict
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import DetailView, ListView, TemplateView

from trail_status.services.prompt_utils import PromptFile, PromptForm

from .models import AreaName, BlogFeed, DataSource, StatusType, TrailCondition

logger = logging.getLogger(__name__)


class SideBarMixin:
    """サイドバー用のフィルター選択肢を取得（データがある項目のみ表示）"""

    @override
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(**_get_sidebar_context())
        return context


class TrailListView(SideBarMixin, ListView):
    """登山道状況一覧ページ（トップページ）のビュー"""

    model = TrailCondition
    queryset = TrailCondition.objects.filter(disabled=False).prefetch_related("source")
    template_name = "trail_status/trail_list.html"

    @override
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.source_filter = request.GET.get("source")
        self.area_filter = request.GET.get("area")
        self.status_filter = request.GET.get("status")

    @override
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_conditions = self.get_queryset()
        datasource = DataSource.web

        # クエリパラメータによる絞り込み
        if self.source_filter:
            base_conditions = base_conditions.filter(source=self.source_filter)
        if self.area_filter:
            base_conditions = base_conditions.filter(area=self.area_filter)
        if self.status_filter:
            base_conditions = base_conditions.filter(status=self.status_filter)
        # 報告日の降順で並べ替え
        filtered_conditions = base_conditions.order_by("-reported_at", "-created_at")

        current_source = self.source_filter
        current_area = self.area_filter
        current_status = self.status_filter

        # 最新の内容更新日（全情報源含む）
        latest_sync_date = self.get_queryset().aggregate(Max("synced_at"))["synced_at__max"]

        # 1週間以内の更新リスト（新規追加情報源は除外）
        # 新規追加情報源 = DataSource.created_atとTrailCondition.updated_atの差が1日以内
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        # @formatter:off
        recent_updated_sources = (
            self.get_queryset()
            .values("source__name", "source__url1")
            .annotate(
                latest_date=Max("synced_at"),
                source_created_at=F("source__created_at"),
                # DataSourceの作成日とTrailConditionの最新更新日の差が1日以内のものを除外
            )
            .filter(latest_date__gt=F("source_created_at") + timedelta(days=1))
            .filter(latest_date__date__gte=seven_days_ago)
            .order_by("-latest_date")
        )
        # @formatter:on

        last_checked_at = datasource.aggregate(Max("last_checked_at"))["last_checked_at__max"]

        context.update(
            {
                "conditions": filtered_conditions,
                "current_source": current_source,
                "current_area": current_area,
                "current_status": current_status,
                "latest_sync_date": latest_sync_date,
                "recent_updated_sources": recent_updated_sources,
                "last_checked_at": last_checked_at,
            }
        )
        return context


class TrailDetailView(SideBarMixin, DetailView):
    """登山道状況個別詳細ページのビュー"""

    model = TrailCondition
    template_name = "trail_status/detail.html"
    context_object_name = "item"

    @override
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ヤマレコ検索リンク生成
        yamareco_base_url = "https://www.yamareco.com/modules/yamareco/search_record.php"
        yamareco_fixed_params = {"isphoto": 1, "request": 1, "submit": "submit"}

        yamareco_area_id = AreaName.get_yamareco_area_id(self.object.area)
        params = {
            "place": self.object.mountain_name_raw,
            "area": yamareco_area_id,
            **yamareco_fixed_params,
        }

        context["yamareco_url"] = f"{yamareco_base_url}?{urllib.parse.urlencode(params, encoding='euc-jp')}"
        return context


class SourceListView(SideBarMixin, ListView):
    """情報源一覧ページのビュー"""

    model = DataSource
    queryset = DataSource.web.order_by("organization_type", "id")
    template_name = "trail_status/sources.html"

    @override
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sources_by_type = defaultdict(list)

        for source in self.get_queryset():
            sources_by_type[source.organization_type].append(source)

        context["sources_by_type"] = dict(sources_by_type)  # Not work in template if defaultdict
        return context


class BlogListView(SideBarMixin, ListView):
    """巡視ブログ一覧ページのビュー"""

    model = DataSource
    template_name = "trail_status/blogs.html"

    @override
    def get_queryset(self):
        # @formatter:off
        queryset = (
            DataSource.objects.filter(data_format="BLOG")
            .prefetch_related(
                Prefetch(
                    "blogfeed_set",
                    queryset=BlogFeed.objects.filter(disabled=False).order_by("-published_at")[:4],
                    to_attr="recent_feeds",
                )
            )
            .order_by("area_name", "id")
        )
        # @formatter:on
        return queryset

    @override
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


class PromptEditView(LoginRequiredMixin, TemplateView):
    template_name = "trail_status/prompt/edit.html"
    login_url = "/trail-p0rtal-dashboard/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["source_id"] = kwargs["source_id"]
        return context


def get_data_source(request, source_id):
    """情報源レコードをJSONで返却"""
    if request.method == "POST":
        return JsonResponse({"error": "Invalid query."})

    try:
        data_source: DataSource = DataSource.objects.get(pk=source_id)
    except DataSource.DoesNotExist:
        return JsonResponse({"error": "No resources found."})
    source_dict = model_to_dict(data_source)
    return JsonResponse(source_dict)


def get_source_list(request):
    """情報源レコードをJSONで返却"""
    if request.method == "POST":
        return JsonResponse({"error": "Invalid query."})

    sources = DataSource.objects.filter(data_format="WEB").values("pk", "name", "prompt_key")
    return JsonResponse(list(sources), safe=False)


# TODO パラメータなしの場合templateを返す（変更検討）
@require_GET
def get_prompt_json(request, source_id=None):
    """プロンプトファイルをJSONで返却

    ファイルがなければ作成
    パラメータなしでテンプレートファイルのデータを返却
    """
    if source_id is None:
        prompt_file = PromptFile.load_template()
    else:
        try:
            data_source = DataSource.objects.get(pk=source_id)
            prompt_filename = data_source.prompt_filename
        except DataSource.DoesNotExist:
            return JsonResponse({"error": "No resources found."}, status=400)

        if data_source.data_format != "WEB":
            return JsonResponse({"error": "Invalid source ID."}, status=400)

        prompt_file = PromptFile.load_site_config(prompt_filename, make_if_missing=True)

    return JsonResponse(prompt_file.model_dump(by_alias=True))


@require_POST
def update_yaml(request, source_id):
    new_data = PromptForm.model_validate(request.POST).to_promptfile()
    new_data.update_site_config()
    logger.debug(str(new_data))
    return JsonResponse({"status": "success", "received": request.POST}, status=200)


def _get_sidebar_context() -> dict:
    """サイドバー用のフィルター選択肢を取得する（データがある項目のみ表示）"""
    base_conditions = TrailCondition.objects.filter(disabled=False).select_related("source")

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
    source_choices = [(id, name) for id, name in DataSource.web.get_labels() if source_counts.get(id, 0) > 0]

    return {
        "source_choices": source_choices,
        "area_choices": area_choices,
        "status_choices": status_choices,
        "recent_sources": list(recent_sources),
    }
