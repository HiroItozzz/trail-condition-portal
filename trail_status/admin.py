from django.contrib import admin
from django.utils import timezone

from .models.condition import TrailCondition
from .models.source import DataSource
from .models.trail import Trail


# 共通ユーティリティ
def format_datetime(dt):
    """日時をフォーマット"""
    return dt.strftime("%Y/%m/%d %H:%M") if dt else "-"


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "org_type_display", "prefecture_code", "url", "last_checked"]
    list_filter = ["name", "organization_type", "prefecture_code"]
    search_fields = ["name", "municipality_code"]

    @admin.display(description="機関種別")
    def org_type_display(self, obj):
        return obj.get_organization_type_display()


@admin.register(Trail)
class TrailAdmin(admin.ModelAdmin):
    list_display = ["name", "area", "mountain", "created_at_short"]
    list_filter = ["area", "mountain", "prefecture_code"]
    search_fields = ["name", "mountain", "municipality"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="登録日")
    def created_at_short(self, obj):
        return obj.created_at.strftime("%Y/%m/%d")


@admin.register(TrailCondition)
class TrailConditionAdmin(admin.ModelAdmin):
    list_display = ["trail", "status", "severity_badge", "title_short", "reported_date", "is_active"]
    list_filter = ["status", "severity", "is_active", "trail__area"]
    search_fields = ["description", "trail__mountain"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "reported_at"

    fieldsets = (
        ("基本情報", {"fields": ("trail", "source", "status", "severity")}),
        ("状況詳細", {"fields": ("title", "description", "location_detail")}),
        ("期間設定", {"fields": ("reported_at", "valid_from", "valid_until", "is_active")}),
        ("メタデータ", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="重要度")
    def severity_badge(self, obj):
        colors = {
            "EMERGENCY": "red",
            "WARNING": "orange",
            "CAUTION": "yellow",
            "INFO": "blue",
        }
        from django.utils.html import format_html

        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            colors.get(obj.severity, "gray"),
            obj.get_severity_display(),
        )

    @admin.display(description="タイトル")
    def title_short(self, obj):
        return obj.title[:30] + "..." if len(obj.title) > 30 else obj.title

    @admin.display(description="報告日", ordering="reported_at")
    def reported_date(self, obj):
        return obj.reported_at.strftime("%m/%d %H:%M")
