# テストカバレッジメモ

## 実効的でないテスト

### test_config_files.py
- `if config_path.exists():` でファイルが存在しない場合も PASSED になる
- `assert config_path.exists()` か `pytest.skip()` に変えるべき

## 漏れているテスト

### test_fetcher.py
- `has_content_changed` に `previous_hash=""` （空文字）を渡したケース
  - `not previous_hash` 修正済みのため動作するはずだが、テストとして明示されていない

### test_pipeline.py
- ハッシュ一致でAI処理がスキップされるケース（`content_changed=False`）
- HTTP失敗・LLM失敗時のエラーハンドリング

### test_db_writer.py（将来）
- `_reconcile_records` 複数レコードケース（現状は1対1のみ）
- `persist_condition_and_usage` / `save_to_source`（DB必要、優先度低）
