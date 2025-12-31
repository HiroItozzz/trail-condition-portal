from django.contrib import admin

from .models.condition import TrailCondition
from .models.mountain import MountainAlias, MountainGroup
from .models.source import DataSource


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "organization_type", "prefecture_code", "url1"]
    list_filter = ["organization_type"]
    search_fields = ["name"]


@admin.register(MountainGroup)
class MountainGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "area_display", "latitude", "longitude", "aliases_count"]
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
    list_display = ["mountain_name_raw", "trail_name", "status", "reported_date", "is_active"]
    list_filter = ["status", "is_active", "source"]
    search_fields = ["mountain_name_raw", "trail_name", "description"]
    date_hierarchy = "reported_at"
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("情報源", {"fields": ("source",)}),
        ("原文情報", {"fields": ("mountain_name_raw", "trail_name", "title", "description", "reported_at")}),
        ("正規化済み情報", {"fields": ("mountain_group", "status")}),
        ("状態管理", {"fields": ("is_active",)}),
        ("メタデータ", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="報告日", ordering="reported_at")
    def reported_date(self, obj):
        return obj.reported_at.strftime("%m/%d %H:%M")
