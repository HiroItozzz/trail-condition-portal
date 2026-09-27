# services/

データ収集パイプライン（取得 → AI 抽出 → レコード照合 → 通知）の実装。

## AI スキーマ
- `types.py` の `ConditionSchemaAi` の `Field(description=...)` は、AI に送るプロンプトの一部になる。書き換えると AI の出力が変わる。
- `ConditionSchemaAiInternal` にフィールドを足したら、`TrailCondition` モデルと `DbWriter.FIELDS_TO_UPDATE` / `_convert_to_internal_schema`（`db_writer.py`）も合わせる。

## LLM のモデルを追加するとき
次の 3 か所をそろえる。
- `types.py` の `LlmModel`
- `llm_stats.py` の `LlmFee._fees`。登録がないと警告ログだけ出して gemini-2.5-pro の料金で計算する
- `trail_sync.py` の `--model` の `choices`

## 落とし穴
- `ConversationalAi.validation_error`（`llm_client.py`）は、構造化出力に失敗するたびに `self.config.temperature` を 0.1 ずつ上げて再試行する。`LlmConfig` を使い回すと temperature が変わったままになる。
- `DbWriter` は `bulk_update` / `bulk_create` で保存するため `auto_now` / `auto_now_add` が効かない。`updated_at` / `created_at` / `synced_at` は手動で入れている。
- `SlackNotifier` / `EmailNotifier` は、設定（`SLACK_WEBHOOK_URL` / `NOTIFICATION_RECIPIENTS`）がないと例外を出さずに送信をスキップする。エラーが出ないことは、送信できたことを意味しない。
- `sample/` の JSON は実際の AI 出力で、意図して git で管理している。`test_matching` コマンドや `tools/` が読み込むので消さない。
