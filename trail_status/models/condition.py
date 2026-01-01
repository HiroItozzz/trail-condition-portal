from django.db import models
from django.utils import timezone

from .mountain import AreaName, MountainGroup
from .source import DataSource


class StatusType(models.TextChoices):
    CLOSURE = "CLOSURE", "🚧 通行止め・閉鎖"
    HAZARD = "HAZARD", "⚠️ 危険箇所・通行注意"
    SNOW = "SNOW", "❄️ 積雪・アイスバーン"
    ANIMAL = "ANIMAL", "🐻 動物出没"
    WEATHER = "WEATHER", "🌧️ 気象警報"
    FACILITY = "FACILITY", "🏠 施設情報"  # 山小屋、トイレなど
    WATER = "WATER", "💧 水場状況"
    OTHER = "OTHER", "📝 その他"


class TrailCondition(models.Model):
    """登山道の状況情報（コアモデル）"""

    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        verbose_name="情報源",
    )
    url1 = models.URLField("情報源URL")

    trail_name = models.CharField("登山道名・区間（原文）", max_length=50)
    mountain_name_raw = models.CharField("山名（原文）", default="", max_length=50, blank=True)
    title = models.CharField("タイトル（原文）", max_length=200)
    description = models.TextField("詳細説明（原文）", blank=True)
    reported_at = models.DateField("報告日", default=timezone.now)
    resolved_at = models.DateField(
        "解消日",
        default=None,
        null=True,
        blank=True,
        help_text="既存の該当項目の登山道状況の問題が解消された場合、あるいは解消される日時が判明した場合にのみ入力",
    )

    # 正規化済み
    status = models.CharField(
        "状況種別",
        max_length=20,
        choices=StatusType.choices,
        default=StatusType.CLOSURE,
    )
    area = models.CharField("山域", max_length=20, choices=AreaName.choices)  # 例: 奥多摩

    reference_URL = models.URLField("補足URL（pdf等）", blank=True)
    comment = models.TextField("備考欄", blank=True)
    mountain_group = models.ForeignKey(
        MountainGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="山グループ",
    )

    # メタデータ
    disabled = models.BooleanField(
        "情報の無効化（管理用）", default=False, help_text="[使用例] 誤情報だった場合ほか"
    )
    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "登山道状態"
        verbose_name_plural = "登山道状態"
        ordering = ["-reported_at"]
        indexes = [
            models.Index(fields=["disabled", "resolved_at", "-reported_at"]),
            models.Index(fields=["area", "status", "disabled", "-reported_at"]),
            models.Index(fields=["mountain_name_raw", "trail_name", "-reported_at"]),
        ]

    def __str__(self):
        return f"{self.trail_name}: {self.status}"

    # 既存情報もAIに投げる場合のメソッド
    def get_raw_fields(self):
        """AI投入用の原文フィールド"""
        return {
            "mountain_name_raw": self.mountain_name_raw,
            "trail_name": self.trail_name,
            "title": self.title,
            "description": self.description,
            "reported_at": self.reported_at,
        }
