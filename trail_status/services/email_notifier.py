import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    登山道状況パイプラインの処理結果をメールで通知するサービス。
    SlackNotifier と同じ呼び出し形式（source_name, updated_count, cost 等）を受け取り、
    件名・本文を組み立てて Django の send_mail（Mailgun SMTP経由）で送信する。
    """

    def __init__(self):
        # settings.py 側で DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_SENDER_NOREPLY', ...) を想定
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.to_emails: list[str] = getattr(settings, "NOTIFICATION_RECIPIENTS", [])

    def send_update_notification(
        self,
        source_name: str,
        updated_count: int,
        created_count: int,
        total_count: int,
        cost: float,
    ) -> None:
        """更新検知時の成功通知メールを送信"""
        subject = f"[trail-info.jp] {source_name} の状況を更新しました"
        body = (
            f"以下の情報源で登山道状況の更新を検知しました。\n\n"
            f"情報源: {source_name}\n"
            f"更新件数: {updated_count}件\n"
            f"新規作成: {created_count}件\n"
            f"合計処理件数: {total_count}件\n"
            f"処理コスト: ${cost:.4f}\n"
        )
        self._send(subject, body)

    def send_error_notification(self, source_name: str, error_message: str) -> None:
        """処理失敗時のエラー通知メールを送信"""
        subject = f"[trail-info.jp] {source_name} の処理でエラーが発生しました"
        body = f"登山道状況の処理中にエラーが発生しました。\n\n情報源: {source_name}\nエラー内容:\n{error_message}\n"
        self._send(subject, body)

    def _send(self, subject: str, body: str) -> None:
        if not self.to_emails:
            logger.warning("NOTIFICATION_RECIPIENTS が未設定のため、メール通知をスキップしました")
            return

        try:
            sended = send_mail(
                subject=subject,
                message=body,
                from_email=self.from_email,
                recipient_list=self.to_emails,
                fail_silently=False,
            )
            if sended == 0:
                logger.error("❌️ メール通知の送信失敗")
            else:
                logger.info(f"✅️ メール通知送信完了: {subject}")

        except Exception as e:
            # メール送信失敗でパイプライン全体を落とさない
            logger.error(f"❌️ メール通知の送信に失敗しました: {e}")
