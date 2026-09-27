# テスト改善の計画（2026-09-27）

テストは 86 件（`uv run pytest --collect-only`）。LLM まわり（クライアント・設定・料金・プロンプト）は厚いが、サービスの中心である照合・パイプライン・画面は薄い。`docs/260322-test-coverage-notes.md` の項目もここに含めた。

## 1. テストが開発用 DB につながる問題（最優先）
- `tests/trail_status/conftest.py` が `django_db_setup` を空のフィクスチャで上書きしているため、テスト用 DB が作られず `DATABASE_URL` の DB をそのまま使う。
- `django_db(transaction=True)` のテスト（`db_writer/test_db_access.py`）は終了時に flush するため、開発用 DB のデータが消える。安心してテストを流せない。
- 対応案：上書きを外し、pytest-django にテスト用 DB を作らせる。
- 未確認：上書きした理由（CI や Supabase で DB を作る権限がなかった、など）。外す前にオーナーに確認する。

## 2. レコード照合の複数件のケース
- `db_writer/test_db_reconcilation.py` は既存レコード 1 件 × AI 結果 1 件のみ。
- `_reconcile_records` の、全ペアの類似度計算 → しきい値判定 → スコア降順の割り当てが試されていない。名寄せの精度の中心なので優先度が高い。

## 3. パイプライン
- `test_pipeline.py` は成功ケースの 1 件のみ。
- 追加するケース：ハッシュ一致で LLM 処理をスキップする（`content_changed=False`）、HTTP の失敗、LLM の失敗。
- `test_fetcher.py`：`has_content_changed` に `previous_hash=""` を渡すケース。

## 4. 画面
- `views/` のテストはステータス 200 とキーワードの確認のみ。
- 追加するケース：`?area=` / `?source=` / `?status=` の絞り込みと、その組み合わせ。

## 5. 通知
- `email_notifier.py` / `slack_notifier.py` のテストがない。
- 追加するケース：成功時・失敗時の送信内容、設定がないときにスキップすること。
- `tools/test/emailtest*.py`（手動のデバッグ用）は、テストに移したら削除する。

## 6. 何も確かめていないテスト
- `test_config_files.py`：3 件とも `if ...exists():` の中で確認しているため、ファイルがなくても通る。`assert ...exists()` にする。
- `db_writer/test_db_access.py`：中身が空。`persist_condition_and_usage` / `save_to_source` のテストにする（1 の対応後）。

## 7. 小さな TODO
- `trail_status/services/prompt_utils.py` の `load_template`：エラー時の戻り値の型。
- `tests/trail_status/conftest.py` の `mock_openai_response`：Response API に合わせたモックにする。

## 進め方
1 はオーナーと方針を決めてから行う。2 以降は仕様が決まれば実装係（implementer）に任せられる大きさ。
