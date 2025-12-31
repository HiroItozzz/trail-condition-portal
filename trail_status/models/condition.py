from django.db import models
from django.utils import timezone

from .mountain import MountainGroup
from .source import DataSource


class TrailCondition(models.Model):
    """登山道の状況情報（コアモデル）"""

    class StatusType(models.TextChoices):
        CLOSURE = "CLOSURE", "🚧 通行止め・閉鎖"
        HAZARD = "HAZARD", "⚠️ 危険箇所・通行注意"
        SNOW = "SNOW", "❄️ 積雪・アイスバーン"
        ANIMAL = "ANIMAL", "🐻 動物出没"
        WEATHER = "WEATHER", "🌧️ 気象警報"
        FACILITY = "FACILITY", "🏠 施設情報"  # 山小屋、トイレなど
        WATER = "WATER", "💧 水場状況"
        OTHER = "OTHER", "📝 その他"

    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        verbose_name="情報源",
    )
    url1 = models.URLField("情報源URL", blank=True)

    trail_name = models.CharField("登山道名・区間（原文）", max_length=50)
    mountain_name_raw = models.CharField("山名（原文）", max_length=50)
    title = models.CharField("タイトル（原文）", max_length=200)
    description = models.TextField("詳細説明（原文）", blank=True)
    reported_at = models.DateTimeField("報告日時", default=timezone.now)

    # 正規化済み
    mountain_group = models.ForeignKey(
        MountainGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="山グループ",
    )

    status = models.CharField(
        "状況種別",
        max_length=20,
        choices=StatusType.choices,
        default=StatusType.CLOSURE,
    )

    # メタデータ
    is_active = models.BooleanField("有効な情報", default=True)
    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "登山道状態"
        verbose_name_plural = "登山道状態"
        ordering = ["-reported_at"]
        indexes = [
            models.Index(fields=["mountain_group", "status", "is_active"]),
            models.Index(fields=["status", "is_active"]),
            models.Index(fields=["reported_at"]),
        ]

    def __str__(self):
        return f"{self.trail_name}: {self.status}"

    def get_raw_fields(self):
        """AI投入用の原文フィールド"""
        return {
            "mountain_name_raw": self.mountain_name_raw,
            "trail_name": self.trail_name,
            "title": self.title,
            "description": self.description,
            "reported_at": self.reported_at,
        }
