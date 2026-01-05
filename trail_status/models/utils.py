from django.db import models


# ユーティリティメソッド
class ChoiceQuerySet(models.QuerySet):
    """ID と name のペアを取得（choices形式）"""
    def get_choices(self):
        if hasattr(self.model, "name"):
            label_field = "name"
        # TrailConditionの場合
        elif hasattr(self.model, "trail_name"):
            label_field = "trail_name"
        else:
            raise AttributeError(f"{self.model.__name__} には 'name' も 'trail_name' も定義されていません。")
        return self.values_list("id", label_field).order_by("id")


class ChoiceManager(models.Manager):
    def get_queryset(self):
        return ChoiceQuerySet(self.model, using=self._db)

    # フィルタリング後も`as_choices`が呼べるための関数
    # models.Managerはmodels.QuerySetのメソッドを自動参照するためロジック的には不要
    def get_choices(self):
        return self.get_queryset().get_choices()
