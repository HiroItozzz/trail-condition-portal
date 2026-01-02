from django.db import models


class OrganizationType(models.TextChoices):
    MUNICIPALITY = "MUNICIPALITY", "地方自治体"
    POLICE_FIRE = "POLICE_FIRE", "警察・消防"
    GOVERNMENT = "GOVERNMENT", "省庁"
    OFFICIAL_DEPS = "OFFICIAL_DEPS", "その他公的機関"
    ASSOCIATION = "ASSOCIATION", "協会・団体"
    MOUNTAIN_HUT = "MOUNTAIN_HUT", "山小屋"
    SNS_USER = "SNS", "SNS/ユーザー投稿"
    OTHER = "OTHER", "その他"


class DataSource(models.Model):
    """情報源となる機関"""

    name = models.CharField("機関名", max_length=200)
    organization_type = models.CharField(
        "機関種別", max_length=50, choices=OrganizationType.choices, default=OrganizationType.ASSOCIATION
    )
    prefecture_code = models.CharField("都道府県コード", max_length=2, default="13", blank=True)  # 東京
    prompt_key = models.CharField(
        "プロンプトキー", max_length=50, unique=True, help_text="例: okutama_vc, kumotori_hut"
    )
    url1 = models.URLField("URL①", max_length=500)
    url2 = models.URLField("URL②", max_length=500, blank=True)
    data_format = models.CharField(
        "データ形式",
        max_length=50,
        choices=[("WEB", "Webページ")],
        default="WEB",
    )
    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "情報源"
        verbose_name_plural = "情報源"
        ordering = ["id"]

    @property
    def prompt_filename(self):
        """プロンプトファイル名: {id:03d}_{prompt_key}.yaml"""
        return f"{self.id:03d}_{self.prompt_key}.yaml"

    def __str__(self):
        return f"{self.name} ({self.get_organization_type_display()})"
