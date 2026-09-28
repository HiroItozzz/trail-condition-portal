# テスト改善の計画（2026-09-27）

テストは 86 件（`uv run pytest --collect-only`）。LLM まわり（クライアント・設定・料金・プロンプト）は厚いが、サービスの中心である照合・パイプライン・画面は薄い。`docs/260322-test-coverage-notes.md` の項目もここに含めた。

## 1. テストが開発用 DB につながる問題（対応済み：2026-09-28）
- `tests/trail_status/conftest.py` が `django_db_setup` を空のフィクスチャで上書きしていたため、テスト用 DB が作られず `DATABASE_URL` の DB をそのまま使っていた。
- 既存のテストでデータが消えなかったのは、`db_writer/test_db_access.py` のクラスでクラス内の `pytestmark = pytest.mark.django_db` が先に入り、デコレータの `transaction=True` が使われていなかったため。`transaction=True` が効くテストでは、終了時の flush で開発用 DB の全テーブルが空になることを確認した。
- 対応：上書きを外し、pytest-django にテスト用 DB（`test_trail_portal_dev`）を作らせた。docker compose の環境で全 86 件が通り、開発用 DB の件数が変わらないことを確認した。

## 2. レコード照合の複数件のケース
- `db_writer/test_db_reconcilation.py` は既存レコード 1 件 × AI 結果 1 件のみ。
- `_reconcile_records` の、全ペアの類似度計算 → しきい値判定 → スコア降順の割り当てが試されていない。名寄せの精度の中心なので優先度が高い。

## 3. パイプライン
- `test_pipeline.py` は成功ケースの 1 件のみ。
- 追加するケース：ハッシュ一致で LLM 処理をスキップする（`content_changed=False`）、HTTP の失敗、LLM の失敗。
- `test_fetcher.py`：`has_content_changed` に `previous_hash=""` を渡すケース。

### 仕様
対象は `AiPipeline`（`trail_status/services/pipeline.py`）と `DataFetcher.has_content_changed`（`fetcher.py`）。本体のコードは変えない。

共通の準備は既存の `test_process_source_data_full_flow` にそろえる。
- HTTP は `mock_async_client`。返す HTML を変えるときは `mock_async_client.get.return_value.text` を差し替える
- `LlmConfig.from_file` は `monkeypatch` で固定の `LlmConfig` を返す
- LLM は `FakeGeminiClient`。LLM が呼ばれたかを見るときは `client_factory` を `MagicMock(side_effect=lambda c: FakeGeminiClient(c))` にする

| # | ケース | 準備 | 期待する結果 |
|---|---|---|---|
| 3-1 | ハッシュ一致で LLM を呼ばない | 本文のある HTML を返す。`content_hash` に `DataFetcher(url).calculate_content_hash(html)` の値を入れる | `success is True`、`content_changed is False`、`new_hash` が `content_hash` と同じ、`extracted_trail_conditions is None`、`client_factory` が呼ばれない |
| 3-2 | ハッシュ一致でも `new_hash_mode=True` なら LLM を呼ぶ | 3-1 と同じ。`AiPipeline(..., new_hash_mode=True)` | `success is True`、`content_changed is True`、`client_factory` が 1 回呼ばれる |
| 3-3 | 取得結果が空 | HTML を `"   "` にする | `success is False`、`message == "スクレイピング結果が空でした"`、`client_factory` が呼ばれない |
| 3-4 | HTTP の失敗 | `mock_async_client.get.side_effect = httpx.ConnectError("接続失敗")`。`fetch_html` の tenacity の待ち時間を `monkeypatch.setattr(DataFetcher.fetch_html.retry, "wait", wait_none())` で 0 にする | `success is False`、`message` が `"処理エラー"` で始まる、`get` が 3 回呼ばれる |
| 3-5 | LLM の失敗 | `_call_api` が `RuntimeError("LLM失敗")` を投げる `FakeGeminiClient` の子クラスを使う | `success is False`、`message` に `"LLM失敗"` を含む |
| 3-6 | 複数の情報源のうち 1 件だけ失敗 | 情報源を 2 件にし、`client_factory` で 1 件目だけ 3-5 のクライアントを返す。`from_file` のモックは情報源のプロンプトを `config.prompt` に入れて返し、`client_factory` はそれを見て切り替える（呼ばれた回数で切り替えると、`asyncio.gather` の実行順に依存するため） | 結果は 2 件で、入力と同じ順。1 件目は `success is False`、2 件目は `success is True` |
| 3-7 | `previous_hash=""` は初回扱い | `test_fetcher.py` に追加。`has_content_changed(html, "")` | 1 つ目が `True`、2 つ目が `calculate_content_hash(html)` と同じ |

完成の条件
- docker compose の `web` で `uv run pytest` が全件通る
- 追加したテストだけで 1 秒以内に終わる（リトライの待ち時間が残っていない）
- 変更したファイルに `ruff check` / `ruff format --check` の新しい違反がない

## 4. 画面
- `views/` のテストはステータス 200 とキーワードの確認のみ。
- 追加するケース：`?area=` / `?source=` / `?status=` の絞り込みと、その組み合わせ。

### 仕様
対象は `TrailListView`（`trail_status/views.py`）の `conditions`。本体のコードは変えない。

- `tests/trail_status/views/test_trail_list.py` に、pytest の書き方（`@pytest.mark.django_db` のクラス、`client` フィクスチャ）でテストを追加する。既存の `TestTrailListView`（`TestCase`）はそのまま残す
- データは `views/conftest.py` の `create_sample_data_source` / `create_sample_condition` で作る。`title` を変えて、どのレコードかを見分ける
- 確かめるのは HTML ではなく `response.context["conditions"]` の `title` の並び。並び順も含めて `list` で比べる
- `transaction=True` は使わない

共通のデータ（どのケースでも同じものを使う）

| title | 情報源 | area | status | reported_at | disabled |
|---|---|---|---|---|---|
| A | 情報源 1 | OKUTAMA | CLOSURE | 今日 − 1 日 | False |
| B | 情報源 1 | TANZAWA | HAZARD | 今日 − 2 日 | False |
| C | 情報源 2 | OKUTAMA | HAZARD | 今日 − 3 日 | False |
| D | 情報源 2 | TANZAWA | CLOSURE | 今日 − 4 日 | False |
| E | 情報源 1 | OKUTAMA | CLOSURE | 今日 | True |

| # | リクエスト | 期待する `title` の並び |
|---|---|---|
| 4-1 | 絞り込みなし | `["A", "B", "C", "D"]`（E は `disabled` なので出ない。`reported_at` の降順） |
| 4-2 | `?area=TANZAWA` | `["B", "D"]` |
| 4-3 | `?source=<情報源 2 の id>` | `["C", "D"]` |
| 4-4 | `?status=HAZARD` | `["B", "C"]` |
| 4-5 | `?area=OKUTAMA&status=CLOSURE` | `["A"]`（E は `disabled`） |
| 4-6 | `?source=<情報源 1 の id>&area=TANZAWA&status=HAZARD` | `["B"]` |
| 4-7 | `?area=HAKONE`（データのない山域） | `[]`、ステータス 200 |
| 4-8 | `?area=`（空の値） | 4-1 と同じ（空文字は絞り込みなし扱い） |

- 4-2〜4-6 は `current_area` / `current_source` / `current_status` がリクエストの値と同じ文字列になることも確かめる
- 4-1〜4-8 は `pytest.mark.parametrize` で 1 つのテストにまとめてもよい（`ids` にケースの内容を書く）。情報源の id はテストの実行時に決まるので、パラメータには情報源の番号（1 / 2）を書き、テストの中で id に置き換える

完成の条件
- docker compose の `web` で `uv run pytest` が全件通る
- 変更したファイルに `ruff check` / `ruff format --check` の新しい違反がない

## 5. 通知
- `email_notifier.py` / `slack_notifier.py` のテストがない。
- 追加するケース：成功時・失敗時の送信内容、設定がないときにスキップすること。
- `tools/test/emailtest*.py`（手動のデバッグ用）は、テストに移したら削除する。

## 6. 何も確かめていないテスト
- `test_config_files.py`：3 件とも `if ...exists():` の中で確認しているため、ファイルがなくても通る。見ているファイル（`prompts/okutama_vc.yaml`、`sample/sample_okutama_vc.txt`、`config/ai_models.yaml`）はどれも既に存在せず、一度も確認していなかった。本物のプロンプトファイルを読むテストは他にもない（`test_prompt_utils.py` / `test_llm_config.py` は `tmp_path` の YAML を使う）。
- `db_writer/test_db_access.py`：中身が空。`persist_condition_and_usage` / `save_to_source` のテストにする。モジュール・クラスのデコレータ・クラス内の 3 か所に `django_db` の印があり、`transaction=True` が効いていないので整理する。

### 仕様（`test_config_files.py` の置き換え）
`tests/trail_status/test_config_files.py` を削除し、`tests/trail_status/test_prompt_files.py` を作る。本物のプロンプトファイルを読み、本番のバッチより先に書き間違いに気づけるようにする。本体のコードは変えない。

対象のファイルは `prompt_utils.get_prompt_dir().glob("[0-9][0-9][0-9]_*.yaml")` を名前順に並べたもの（今は `001_okutama_vc.yaml`〜`008_tokyo_akiruno.yaml`）。`example.yaml` / `sample_tanzawa_vc.yaml` / `template.yaml` は含めない。ファイルが増えたら自動で対象になるようにし、ファイル名は直接書かない。

| # | テスト | 期待する結果 |
|---|---|---|
| 6-1 | 対象のファイルが見つかる | 1 件以上ある（`parametrize` の値が空だとテストが skip になり、何も確かめずに通るため、別のテストで確かめる） |
| 6-2 | YAML のキーに書き間違いがない | 各ファイルを `yaml.safe_load` で読む。トップレベルのキーが `{"prompt", "config"}` に含まれる。`config` があれば、そのキーが `PromptFileConfig.model_fields` の名前か、その alias（`to_camel` の値）に含まれる。`PromptFile` は知らないキーを黙って無視するため、このテストで見つける |
| 6-3 | テンプレートと合わせて `LlmConfig` が作れる | `mock_api_keys` を使う。`PromptFile.load_merged_config(name, url="https://example.com/")` → `LlmConfig.from_file(prompt_file, data="テスト")` が例外なく終わる（モデル名・temperature の範囲は `LlmConfig` のバリデーションで確かめられる）。`config.prompt` が空でない、`config.prompt_filename == name` |

- 6-2 と 6-3 は `pytest.mark.parametrize` で対象のファイルごとに 1 件にし、`ids` にファイル名を使う
- `load_site_config` はファイルがないと `example.yaml` をコピーして作るため、対象は必ず glob で見つかったファイルに限る

完成の条件
- docker compose の `web` で `uv run pytest` が全件通る
- 試しに 1 つのファイルの `temperature` を `temprature` に書き換えると 6-2 が失敗することを確かめ、元に戻す（`git diff` でプロンプトファイルに差分が残っていないこと）
- 変更したファイルに `ruff check` / `ruff format --check` の新しい違反がない

## 6.5 プロンプトファイルの読み込みの失敗（テスト以外の改善）
- `trail_sync.py` の `setup_data_source` は、全情報源の `PromptFile.load_merged_config` を `try` なしで呼ぶ。1 つの YAML が壊れているだけで、全情報源の処理が止まる。
- モデル名・temperature の誤りは `pipeline.py` の `try/except` で、その情報源だけの失敗になる。読み込みの失敗も同じ扱いにするかを決める。
- 6 のテストで事前に気づけるようになるため、優先度は低い。

## 7. 小さな TODO
- `trail_status/services/prompt_utils.py` の `load_template`：エラー時の戻り値の型。
- `tests/trail_status/conftest.py` の `mock_openai_response`：Response API に合わせたモックにする。

## 進め方
2 以降は仕様が決まれば実装係（implementer）に任せられる大きさ。
