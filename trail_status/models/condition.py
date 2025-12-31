from django.db import models
from django.utils import timezone

from .source import DataSource
from .trail import Trail


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

    trail = models.ForeignKey(
        Trail,
        on_delete=models.CASCADE,
        verbose_name="登山道",
        related_name="statuses",
    )
    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        verbose_name="情報源",
    )

    status = models.CharField(
        "状況種別",
        max_length=20,
        choices=StatusType.choices,
        default=StatusType.CLOSURE,
    )
    severity = models.CharField(
        "重要度",
        max_length=10,
        choices=[
            ("EMERGENCY", "緊急"),
            ("WARNING", "警告"),
            ("CAUTION", "注意"),
            ("INFO", "情報"),
        ],
        default="INFO",
    )

    # 状況詳細
    title = models.CharField("タイトル", max_length=200)
    description = models.TextField("詳細説明", blank=True)
    location_detail = models.CharField("詳細位置", max_length=300, blank=True)  # 例: "○○登山道 2合目〜3合目"

    # 期間
    reported_at = models.DateTimeField("報告日時", default=timezone.now)
    valid_from = models.DateTimeField("有効開始", default=timezone.now)
    valid_until = models.DateTimeField("有効期限", null=True, blank=True)

    # メタデータ
    is_active = models.BooleanField("有効な情報", default=True)
    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "状況情報"
        verbose_name_plural = "状況情報"
        ordering = ["-reported_at", "-severity"]
        indexes = [
            models.Index(fields=["trail", "status"]),
            models.Index(fields=["status", "severity"]),
            models.Index(fields=["valid_until", "is_active"]),
        ]

    def __str__(self):
        return f"{self.trail.name}: {self.status}"

    def is_current(self):
        """現在有効な状況かチェック"""
        now = timezone.now()
        if self.valid_until and self.valid_until < now:
            return False
        if self.valid_from > now:
            return False
        return self.is_active
