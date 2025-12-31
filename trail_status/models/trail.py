from django.db import models

from .source import DataSource


class Trail(models.Model):
    """登山道基本情報"""

    class AreaName(models.TextChoices):
        OKUTAMA = "OKUTAMA", "奥多摩"
        TANZAWA = "TANZAWA", "丹沢"
        TAKAO = "TAKAO", "高尾・奥高尾"
        HAKONE = "HAKONE", "箱根"
        OKUMUSASHI = "OKUMUSASHI", "奥武蔵"
        OKUCHICHIBU = "OKUCHICHIBU", "奥秩父"
        DAIBOSATSU = "DAIBOSATSU", "大菩薩連嶺"

    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, verbose_name="情報源")

    name = models.CharField("登山道名/区間名", max_length=50)
    mountain = models.CharField("山名", max_length=20)  # 例: 雲取山、塔ノ岳
    area = models.CharField(
        "山域",
        max_length=20,
        choices=AreaName.choices,
        default=AreaName.OKUTAMA,
    )  # 例：奥多摩、丹沢
    location_description = models.TextField("位置説明", blank=True)

    prefecture_code = models.CharField(
        "都道府県コード",
        max_length=2,
        default="13",
        blank=True,
        null=True,
    )
    municipality = models.CharField(
        "市区町村コード",
        max_length=5,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "登山道"
        verbose_name_plural = "登山道"
        indexes = [
            models.Index(fields=["prefecture_code", "municipality"]),
            models.Index(fields=["area"]),
            models.Index(fields=["mountain"]),
        ]

    def __str__(self):
        return f"{self.mountain} ({self.area})"
