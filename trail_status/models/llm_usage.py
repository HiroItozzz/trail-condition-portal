from decimal import Decimal

from django.db import models

from .source import DataSource


class LlmUsage(models.Model):
    """LLM利用履歴とコスト管理"""

    # 基本情報
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, verbose_name="情報源")
    model = models.CharField("LLMモデル", max_length=50)

    # トークン情報
    prompt_tokens = models.IntegerField("入力トークン数",default=0)
    thinking_tokens = models.IntegerField("思考トークン数", default=0)
    output_tokens = models.IntegerField("出力トークン数",default=0)

    # コスト情報
    cost_usd = models.DecimalField("コスト(USD)", max_digits=10, decimal_places=6, default=Decimal("0.000000"))

    # 成果情報
    conditions_extracted = models.IntegerField("抽出された状況数", default=0)
    success = models.BooleanField("処理成功", default=True)

    # メタデータ
    executed_at = models.DateTimeField("実行日時", auto_now_add=True)
    execution_time_seconds = models.FloatField("実行時間(秒)", null=True, blank=True)

    class Meta:
        verbose_name = "LLM利用履歴"
        verbose_name_plural = "LLM利用履歴"
        ordering = ["-executed_at"]
        indexes = [
            models.Index(fields=["executed_at", "model"]),
            models.Index(fields=["source", "-executed_at"]),
        ]

    @property
    def cost_per_condition(self):
        """1件あたりのコスト"""
        if self.conditions_extracted and self.conditions_extracted > 0:
            return self.cost_usd / self.conditions_extracted
        return Decimal("0")

    @property
    def total_tokens(self):
        """総トークン数"""
        return self.prompt_tokens + self.thinking_tokens + self.output_tokens

    def __str__(self):
        return f"{self.source.name} - {self.model} ({self.executed_at.strftime('%Y-%m-%d %H:%M')})"
