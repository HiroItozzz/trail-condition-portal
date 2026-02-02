import os
import subprocess
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from google.cloud import storage


class Command(BaseCommand):
    help = "PostgreSQLデータベースのバックアップをCloud Storageに保存"

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        backup_file = f"{timestamp}_backup.dump"
        local_path = f"/tmp/{backup_file}"

        try:
            self.stdout.write("データベースバックアップを開始...")

            # pg_dumpでバックアップ作成
            subprocess.run(
                ["pg_dump", "--dbname", os.environ["DATABASE_URL"], "--format=custom", "--file", local_path],
                check=True,
                capture_output=True,
                text=True,
            )
            self.stdout.write(self.style.SUCCESS(f"✓ バックアップ作成: {local_path}"))

            # Cloud Storageにアップロード
            client = storage.Client()
            bucket = client.bucket("trail-info-backup_data")
            blob = bucket.blob(f"database/{backup_file}")
            blob.upload_from_filename(local_path)
            self.stdout.write(self.style.SUCCESS(f"✓ アップロード完了: gs://{bucket.name}/{blob.name}"))

            # ローカルファイル削除
            os.remove(local_path)
            self.stdout.write("✓ ローカルファイル削除完了")

            self.stdout.write(self.style.SUCCESS("バックアップ完了"))

        except subprocess.CalledProcessError as e:
            raise CommandError(f"pg_dumpエラー: {e.stderr}")
        except Exception as e:
            # ローカルファイルが残っている場合は削除
            if os.path.exists(local_path):
                os.remove(local_path)
            raise CommandError(f"バックアップ失敗: {str(e)}")
