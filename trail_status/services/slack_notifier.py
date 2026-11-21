import logging
from typing import Optional

import httpx2
from django.conf import settings

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slack Webhook API を使用した通知クライアント"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Args:
            webhook_url: Slack Webhook URL（省略時は環境変数から取得）
        """
        self.webhook_url = webhook_url or getattr(settings, "SLACK_WEBHOOK_URL", None)
        self.enabled = bool(self.webhook_url)

    def send_update_notification(
        self,
        source_name: str,
        updated_count: int,
        created_count: int,
        total_count: int,
        cost: float,
    ) -> bool:
        """
        trail_sync完了時に更新情報をSlackに送信

        Args:
            source_name: 情報源名（例: 奥多摩ビジターセンター）
            updated_count: 更新されたレコード数
            created_count: 新規作成レコード数
            total_count: 総レコード数
            cost: AIモデル使用コスト（USD）

        Returns:
            送信成功時 True
        """
        if not self.enabled:
            logger.debug("Slack Webhook URLが設定されていないため、通知をスキップします")
            return False

        try:
            # 変更があった場合のみハイライト
            if updated_count > 0 or created_count > 0:
                emoji = "🔔"
                color = "warning"
            else:
                emoji = "📝"
                color = "good"

            message = {
                "text": f"{emoji} 登山道情報の更新: {source_name}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {"title": "情報源", "value": source_name, "short": True},
                            {"title": "更新", "value": str(updated_count), "short": True},
                            {"title": "新規作成", "value": str(created_count), "short": True},
                            {"title": "総計", "value": str(total_count), "short": True},
                            {"title": "AI処理コスト", "value": f"${cost:.4f}", "short": True},
                        ],
                    }
                ],
            }

            response = httpx2.post(self.webhook_url, json=message, timeout=10)
            response.raise_for_status()
            logger.info(f"Slack通知を送信しました: {source_name}")
            return True

        except Exception as e:
            logger.error(f"Slack通知の送信に失敗しました: {e}")
            return False

    def send_error_notification(self, source_name: str, error_message: str) -> bool:
        """
        エラー発生時にSlackに通知

        Args:
            source_name: 情報源名
            error_message: エラーメッセージ

        Returns:
            送信成功時 True
        """
        if not self.enabled:
            return False

        try:
            message = {
                "text": f"❌ 登山道情報同期エラー: {source_name}",
                "attachments": [
                    {
                        "color": "danger",
                        "fields": [
                            {"title": "情報源", "value": source_name, "short": True},
                            {"title": "エラー内容", "value": error_message, "short": False},
                        ],
                    }
                ],
            }

            response = httpx2.post(self.webhook_url, json=message, timeout=10)
            response.raise_for_status()
            logger.info(f"Slackエラー通知を送信しました: {source_name}")
            return True

        except Exception as e:
            logger.error(f"Slackエラー通知の送信に失敗しました: {e}")
            return False
