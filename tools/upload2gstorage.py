"""
コマンド:
uv run tools/upload2gstorage.py

"""

from pathlib import Path

from google.cloud import storage

BUCKET_NAME = ""


def upload():

    local_paths = Path.cwd() / "tools/grid/samples/raw"
    cnt = 0
    for p in local_paths.glob("*/*"):
        # Cloud Storageにアップロード
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"{p.parent.name}/{p.name}")
        blob.upload_from_filename(p)
        cnt += 1
        print(f"✓ {cnt}件目アップロード完了: gs://{bucket.name}/{blob.name}")

    print(f"全件アップロード完了: {cnt}件")


if __name__ == "__main__":
    upload()
