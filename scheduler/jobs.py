import logging
from django.core.management import call_command

logger = logging.getLogger(__name__)

def sync_trail_conditions_job():
    """登山道状況同期ジョブ"""
    logger.info("定期ジョブ開始: trail_sync")
    try:
        # 管理コマンドをプログラムから呼び出す
        call_command("trail_sync", dry_run=True, source=3, model="deepseek-chat")
        logger.info("定期ジョブ完了: trail_sync")
    except Exception as e:
        logger.error(f"定期ジョブ失敗: {e}", exc_info=True)
