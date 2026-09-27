# tests/

`trail_status/` の構成に対応している（`tests/trail_status/commands/`、`db_writer/`、`llm/`、`views/` など）。新しいテストは対応するディレクトリに置く。

## DB を使うテストは開発用 DB に直接つながる
- `tests/trail_status/conftest.py` の `django_db_setup` を空のフィクスチャで上書きしているため、テスト用 DB は作られない。`@pytest.mark.django_db` のテストは `DATABASE_URL` の DB をそのまま使う。
- 事前に `uv run python manage.py migrate` が必要。
- `django_db(transaction=True)` のテストは、終了時にテーブルを空にする（flush）。開発用 DB のデータが消える。

## 外部 API
- LLM クライアントに触れるテストは `mock_api_keys` を明示的に使う（autouse ではない）。キーがないと `ValueError` になる。
- HTTP 取得のモックは `mock_async_client` を使う。
- プロンプトのキャッシュのクリア、LangSmith の無効化、AI 出力サンプルの保存の無効化は、autouse のフィクスチャが毎回行う。
