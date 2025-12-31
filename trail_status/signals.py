from django.db.models.signals import post_save
from django.dispatch import receiver

from .models.condition import TrailCondition
from .models.mountain import MountainAlias


@receiver(post_save, sender=MountainAlias)
def update_existing_conditions(sender, instance, created, **kwargs):
    """
    MountainAlias が新規作成されたとき、
    既存の TrailCondition を自動更新
    """
    if created:  # 新規作成時のみ（更新時は実行しない）
        TrailCondition.objects.filter(mountain_name_raw=instance.alias_name, mountain_group_id__isnull=True).update(
            mountain_group=instance.mountain_group,
        )
