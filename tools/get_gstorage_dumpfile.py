import argparse
import subprocess
from pathlib import Path

from google.cloud import storage

BUCKET_NAME = "trail-info-backup_data"
OUTPUT_DIR = Path.cwd() / "backups"


def save_blob():
    try:
        blob = get_latest_blob(BUCKET_NAME)
        output_path = OUTPUT_DIR / blob.name.rsplit("/", 1)[-1]
        OUTPUT_DIR.mkdir(exist_ok=True)

        blob.download_to_filename(output_path)

    except Exception as e:
        print("ダンプファイルのダウンロード中にエラー発生。詳細: ")
        raise e

    print(f"ダンプファイルのダウンロード完了。場所: {output_path}")
    return output_path


def get_latest_blob(bucket_name):
    """Lists all the blobs in the bucket."""
    # bucket_name = "your-bucket-name"

    storage_client = storage.Client()

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(bucket_name)

    # Note: The call returns a response only when the iterator is consumed.
    blob = sorted(blobs, key=lambda x: x.name, reverse=True)[0]
    print(f"最新のバックアップファイル: {blob.name}")

    return blob


def run_pg_restore(filepath: Path):
    try:
        with open(filepath, "rb") as f:
            subprocess.run(
                ["docker", "compose", "exec", "-e", "PGPASSWORD=password", "-T", "db",
                 "pg_restore", "-U", "user", "-d", "trail_portal_dev", "--clean", "--if-exists"],
                stdin=f
            )
        print("Postgresコンテナのデータ復元完了")
        return 0

    except FileNotFoundError as e:
        print(f"ダンプファイルが見つかりません: {e}")
        return 1
    except Exception as e:
        print(f"Dockerコマンド実行中にエラー: {e}")
        return 1


if __name__ == "__main__":
    exit_code = 0
    dumpfile_path: Path = save_blob()

    parser = argparse.ArgumentParser(description="get postgres dumpfile from Google Cloud Storage.",
                                     usage="python restore_db.py [--restore]")
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    if args.restore:
        exit_code = run_pg_restore(dumpfile_path)
    exit(exit_code)
