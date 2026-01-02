from django.contrib import admin

from .models.condition import TrailCondition
from .models.llm_usage import LlmUsage
from .models.mountain import MountainAlias, MountainGroup
from .models.source import DataSource


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "prompt_key", "organization_type", "prefecture_code", "url1"]
    list_filter = ["organization_type"]
    search_fields = ["name"]


@admin.register(MountainGroup)
class MountainGroupAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "area_display", "latitude", "longitude", "aliases_count"]
    list_filter = ["area"]
    search_fields = ["name"]

    @admin.display(description="山域")
    def area_display(self, obj):
        return obj.get_area_display()

    @admin.display(description="含まれる山数/別名数")
    def aliases_count(self, obj):
        return obj.aliases.count()


@admin.register(MountainAlias)
class MountainAliasAdmin(admin.ModelAdmin):
    list_display = ["alias_name", "mountain_group"]
    list_filter = ["mountain_group"]
    search_fields = ["alias_name", "mountain_group__name"]


@admin.register(TrailCondition)
class TrailConditionAdmin(admin.ModelAdmin):
    list_display = [
        "mountain_name_raw",
        "trail_name",
        "title",
        "description",
        "comment",
        "source",
        "url1",
        "area",
        "status",
        "reported_at",
        "resolved_at",
        "disabled",
    ]
    list_filter = ["disabled", ("resolved_at", admin.EmptyFieldListFilter), "status", "area", "source"]
    search_fields = ["mountain_name_raw", "trail_name", "description"]
    date_hierarchy = "reported_at"
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("情報源", {"fields": ("source", "url1")}),
        (
            "原文情報",
            {
                "fields": (
                    "mountain_name_raw",
                    "trail_name",
                    "area",
                    "title",
                    "description",
                    "reported_at",
                    "resolved_at",
                )
            },
        ),
        ("正規化済み情報", {"fields": ("status", "mountain_group")}),
        ("管理", {"fields": ("disabled",)}),
        ("メタデータ", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="報告日", ordering="reported_at")
    def reported_date(self, obj):
        return obj.reported_at.strftime("%m/%d %H:%M")


@admin.register(LlmUsage)
class LlmUsageAdmin(admin.ModelAdmin):
    list_display = [
        "executed_at",
        "source",
        "model",
        "cost_usd",
        "conditions_extracted",
        "total_tokens",
        "execution_time_seconds",
        "success",
    ]
    list_filter = [
        "model",
        "success",
        ("executed_at", admin.DateFieldListFilter),
        "source",
    ]
    search_fields = ["source__name", "model"]
    date_hierarchy = "executed_at"
    readonly_fields = [
        "executed_at",
        "cost_per_condition",
        "total_tokens",
    ]

    fieldsets = (
        ("実行情報", {"fields": ("source", "model", "executed_at", "execution_time_seconds", "success")}),
        ("トークン情報", {"fields": ("prompt_tokens", "thinking_tokens", "output_tokens", "total_tokens")}),
        ("コスト情報", {"fields": ("cost_usd", "cost_per_condition")}),
        ("成果情報", {"fields": ("conditions_extracted",)}),
    )

    @admin.display(description="実行日時", ordering="executed_at")
    def execution_date(self, obj):
        return obj.executed_at.strftime("%m/%d %H:%M")

    @admin.display(description="1件あたりコスト")
    def cost_per_item(self, obj):
        return f"${obj.cost_per_condition:.4f}" if obj.conditions_extracted > 0 else "-"
