from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AreaName(models.TextChoices):
    OKUTAMA = "OKUTAMA", "奥多摩"
    TANZAWA = "TANZAWA", "丹沢"
    TAKAO = "TAKAO", "高尾・奥高尾"
    HAKONE = "HAKONE", "箱根"
    OKUMUSASHI = "OKUMUSASHI", "奥武蔵"
    OKUCHICHIBU = "OKUCHICHIBU", "奥秩父"
    DAIBOSATSU = "DAIBOSATSU", "大菩薩連嶺"


class MountainGroup(models.Model):
    """ユーザー視点の山名（厳選）"""

    name = models.CharField("山名", max_length=50, unique=True)  # 例: 雲取山、大岳山、御岳山

    area = models.CharField("山域", max_length=20, choices=AreaName.choices)  # 例: 奥多摩

    # 地図表示用の代表座標
    latitude = models.DecimalField(
        "緯度",
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(20),  # 日本最南端より南
            MaxValueValidator(50),  # 日本最北端より北
        ],
    )
    longitude = models.DecimalField(
        "経度",
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(120),  # 日本最西端より西
            MaxValueValidator(160),  # 日本最東端より東
        ],
    )

    class Meta:
        verbose_name = "山グループ"
        verbose_name_plural = "山グループ"
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_area_display()})"


class MountainAlias(models.Model):
    """山の別名・マイナー山名"""

    mountain_group = models.ForeignKey(
        MountainGroup, on_delete=models.CASCADE, related_name="aliases", verbose_name="山グループ"
    )
    alias_name = models.CharField("別名・マイナー山名", max_length=50, unique=True)

    class Meta:
        verbose_name = "山名別名"
        verbose_name_plural = "山名別名"

    def __str__(self):
        return f"{self.alias_name} → {self.mountain_group.name}"
