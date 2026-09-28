# tests/

`trail_status/` の構成に対応している（`tests/trail_status/commands/`、`db_writer/`、`llm/`、`views/` など）。新しいテストは対応するディレクトリに置く。

## DB を使うテストはテスト用 DB を使う
- pytest-django が、`DATABASE_URL` の DB 名の頭に `test_` をつけた DB（例：`test_trail_portal_dev`）を作り、マイグレーションを適用する。終了時に削除する。開発用 DB のデータには触れない。
- DB を作るため、`DATABASE_URL` のユーザーに `CREATEDB` の権限が必要。
- `django_db_setup` を上書きしない。空のフィクスチャで上書きすると、テストが `DATABASE_URL` の DB に直接つながり、`django_db(transaction=True)` のテストの終了時の flush で全テーブルが空になる。

## 外部 API
- LLM クライアントに触れるテストは `mock_api_keys` を明示的に使う（autouse ではない）。キーがないと `ValueError` になる。
- HTTP 取得のモックは `mock_async_client` を使う。
- プロンプトのキャッシュのクリア、LangSmith の無効化、AI 出力サンプルの保存の無効化は、autouse のフィクスチャが毎回行う。
