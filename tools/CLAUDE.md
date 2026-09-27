# tools/

オーナーが手で実行するスクリプト。`.dockerignore` で除外されており、本番のイメージには入らない。

- `get_gstorage_dumpfile.py` は、GCS から本番 DB のダンプをダウンロードする。`--restore` をつけると、docker compose の `db` サービスの DB を丸ごと上書きする。本番のデータを含むため、オーナーの指示なしに実行しない。
