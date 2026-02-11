from django.db import models

from .mountain import AreaName
from .source import DataSource


class BlogFeed(models.Model):
    title = models.CharField("記事のタイトル", max_length=100)
    summary = models.TextField("記事の冒頭", max_length=200)
    url = models.URLField("記事へのリンクURL", max_length=500)
    source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, limit_choices_to={"data_format": "BLOG"}, verbose_name="情報源"
    )
    published_at = models.DateTimeField("投稿日時")
    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    disabled = models.BooleanField("情報の無効化フラグ", default=False, help_text="[使用例] 誤情報だった場合ほか")
    
    class Meta:
        verbose_name = "巡回ブログ"
        verbose_name_plural = "巡回ブログ"
        ordering = ["-published_at"]
    
    def __str__(self):
        return f"{self.source.name}: {self.title}"