from django.db import models


class PromptBackup(models.Model):
    """プロンプトファイルの定期バックアップ"""
    
    file_name = models.CharField("ファイル名", max_length=100, db_index=True, help_text="例: 001_okutama_vc.yaml")
    content = models.TextField("プロンプト内容")
    backup_date = models.DateTimeField("バックアップ日時", auto_now_add=True)
    file_hash = models.CharField("ファイルハッシュ", max_length=64, unique=True, help_text="SHA256ハッシュ")
    file_size = models.IntegerField("ファイルサイズ(bytes)", default=0)
    backup_type = models.CharField(
        "バックアップ種別", 
        max_length=20, 
        choices=[
            ("scheduled", "定期"),
            ("manual", "手動"), 
            ("emergency", "緊急")
        ],
        default="scheduled"
    )
    
    class Meta:
        verbose_name = "プロンプトバックアップ"
        verbose_name_plural = "プロンプトバックアップ"
        ordering = ['-backup_date']
        indexes = [
            models.Index(fields=['file_name', '-backup_date']),
            models.Index(fields=['backup_type', '-backup_date']),
        ]
    
    def __str__(self):
        return f"{self.file_name} ({self.backup_date.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def content_preview(self):
        """管理画面用のプレビュー（最初の100文字）"""
        return self.content[:100] + "..." if len(self.content) > 100 else self.content