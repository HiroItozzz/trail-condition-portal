from google.cloud import storage
from pathlib import Path

BUCKET_NAME = "trail-info-backup_data"
OUTPUT_PATH = Path.cwd() / "backups"


def save_blob():
    try:
        blob = get_latest_blob(BUCKET_NAME)

        name = blob.name.rsplit("/", 1)[-1]

        OUTPUT_PATH.mkdir(exist_ok=True)

        blob.download_to_filename(OUTPUT_PATH / name)

        print(f"ダンプファイルのダウンロード完了。場所: {OUTPUT_PATH}")
    except Exception as e:
        print("ダンプファイルのダウンロード中にエラー発生。詳細: ")
        raise e


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


if __name__ == "__main__":
    save_blob()
