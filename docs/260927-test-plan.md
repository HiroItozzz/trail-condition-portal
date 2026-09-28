# テスト改善の計画（2026-09-27）

計画を立てた時点のテストは 86 件（`uv run pytest --collect-only`）。LLM まわり（クライアント・設定・料金・プロンプト）は厚いが、サービスの中心である照合・パイプライン・画面は薄い。`docs/260322-test-coverage-notes.md` の項目もここに含めた。

## 1. テストが開発用 DB につながる問題（対応済み：2026-09-28）
- `tests/trail_status/conftest.py` が `django_db_setup` を空のフィクスチャで上書きしていたため、テスト用 DB が作られず `DATABASE_URL` の DB をそのまま使っていた。
- 既存のテストでデータが消えなかったのは、`db_writer/test_db_access.py` のクラスでクラス内の `pytestmark = pytest.mark.django_db` が先に入り、デコレータの `transaction=True` が使われていなかったため。`transaction=True` が効くテストでは、終了時の flush で開発用 DB の全テーブルが空になることを確認した。
- 対応：上書きを外し、pytest-django にテスト用 DB（`test_trail_portal_dev`）を作らせた。docker compose の環境で全 86 件が通り、開発用 DB の件数が変わらないことを確認した。

## 2. レコード照合の複数件のケース
- `db_writer/test_db_reconcilation.py` は既存レコード 1 件 × AI 結果 1 件のみ。
- `_reconcile_records` の、全ペアの類似度計算 → しきい値判定 → スコア降順の割り当てが試されていない。名寄せの精度の中心なので優先度が高い。
- テストは 2 層に分ける。
  - A：割り当てのしくみ。類似度を表で決めて確かめる。正解はコードの設計から決まる
  - B：類似度の質。本物の Sudachi + RapidFuzz で「同じ登山道」と判定されるか。正解はオーナーが決める（`sample/` の実際の AI 出力からペアを選ぶ）
- 照合の流れとテストの 2 層の考え方は `docs/260215-record-matching-simple.md` にまとめた。
- 決定（2026-09-28）：どの AI 出力とも結びつかなかった既存レコードは、何もせずに残す（意図した挙動）。A の仕様ではこの挙動を assert していないため、固定するテストは別に足す。

### 仕様（A：割り当てのしくみ）
対象は `DbWriter._reconcile_records`（`trail_status/services/db_writer.py`）。本体のコードは変えない。

- `tests/trail_status/db_writer/test_db_reconcilation.py` に、新しいクラスで追加する。既存のフィクスチャ `mock_DbWriter` を使う。既存のテストは変えない
- 類似度は `monkeypatch.setattr(DbWriter, "_calculate_similarity", ...)` で差し替え、`(既存レコードの id, AI 出力の title)` をキーにした dict から返す。dict にない組み合わせは 0.0
- 既存レコードは既存の `mock_existing_record` と同じく `MagicMock(spec=TrailCondition, ...)` で作る（DB は使わない）。`id`、`disabled`、`status`、`resolved_at` を指定する
- AI 出力は `ConditionSchemaAiInternal` で作り、`title` で見分ける（`"a"`、`"b"` など）
- どの AI 出力と結びついたかは、更新されたレコードの `title` で見る（更新時に AI 出力の `title` がコピーされる）。そのため、結びつくことを確かめたいペアは、既存の `status` を `CLEAR`、AI 出力の `status` を `CLOSURE` にして更新が起きるようにする
- しきい値は数値を直接書かず `DbWriter.SIMILARITY_THRESHOLD` を使う

| # | 既存 | AI 出力（渡す順） | 類似度 | 期待する結果 |
|---|---|---|---|---|
| A-1 | X | a, b | X-a: 0.95、X-b: 0.80 | `to_update` は X だけで `X.title == "a"`。`to_create` の title は `["b"]`（0.7 以上でも、取り合いに負けたら新規） |
| A-2 | X | b, a（A-1 の逆順） | A-1 と同じ | A-1 と同じ（渡す順ではなくスコアで決まる） |
| A-3 | X, Y | a, b | X-a: 0.90、Y-a: 0.85、X-b: 0.80、Y-b: 0.75 | X ← a、Y ← b。`to_create` は空（a が X を取ったあと、b は残った Y と結びつく） |
| A-4 | X, Y | a, b | X-a: `THRESHOLD`、Y-b: `THRESHOLD - 0.01` | X ← a。`to_create` の title は `["b"]`（しきい値ちょうどは結びつく） |
| A-5 | X（`disabled=True`） | a | X-a: 1.0 | `to_update` は空。`to_create` の title は `["a"]` で、`disabled is False`（既存レコードがあるので初回ではない） |
| A-6 | X, Y | a, b | X-a: 0.9、Y-b: 0.9。X と a は `status` も `resolved_at` も同じ。Y と b は `status` が違う | `to_update` は Y だけ。`to_create` は空（変更のないペアは更新も新規もしない） |

- A-1〜A-6 は既存レコードの `id` が 1 から始まらなくても動くように、`id` は 101、102 のように決める
- 結びつかなかった既存レコードについては assert しない（固定するテストは A-7 で足す）

#### A-7（追加）：結びつかなかった既存レコードは残す
A-1〜A-6 と同じ準備で、`TestReconcileRecordsAssignment` に 1 件足す。

| # | 既存 | AI 出力 | 類似度 | 期待する結果 |
|---|---|---|---|---|
| A-7 | X、Y（どちらも `status=CLEAR`、`disabled=False`、`resolved_at=None`） | a（`status=CLOSURE`） | X-a: 0.9 | `to_update` の title は `["a"]` で、`to_update` に Y が含まれない。`to_create` は空。Y の `disabled` は `False`、`status` は `CLEAR`、`resolved_at` は `None` のまま |

完成の条件
- docker compose の `web` で `uv run pytest` が全件通る
- 試しに `_reconcile_records` の `matches.sort(..., reverse=True)` を `reverse=False` にすると、A-1 と A-2 が失敗することを確かめ、元に戻す（`git diff` で `db_writer.py` に差分が残っていないこと）
- 変更したファイルに `ruff check` / `ruff format --check` の新しい違反がない

## 3. パイプライン（対応済み：2026-09-28）
- 対応前の `test_pipeline.py` は成功ケースの 1 件のみだった。
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
| 3-6 | 複数の情報源のうち 1 件だけ失敗 | 情報源を 2 件にし、`client_factory` で 1 件目だけ 3-5 のクライアントを返す。`from_file` のモックは情報源のプロンプトを `config.prompt` に入れて返し、`client_factory` はそれを見て切り替える（呼ばれた回数で切り替えると、`asyncio.gather` の実行順に依存するため） | 結果は 2 件で、入力と同じ順。1 件目は `success is False` で `message` に `"LLM失敗"` を含む（別の理由の失敗と見分けるため）、2 件目は `success is True` |
| 3-7 | `previous_hash=""` は初回扱い | `test_fetcher.py` に追加。`has_content_changed(html, "")` | 1 つ目が `True`、2 つ目が `calculate_content_hash(html)` と同じ |

完成の条件
- docker compose の `web` で `uv run pytest` が全件通る
- 追加したテストだけで 1 秒以内に終わる（リトライの待ち時間が残っていない）
- 変更したファイルに `ruff check` / `ruff format --check` の新しい違反がない

## 4. 画面（対応済み：2026-09-28）
- 対応前の `views/` のテストはステータス 200 とキーワードの確認のみだった。
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

## 6. 何も確かめていないテスト（対応済み：2026-09-28）
以下は対応前の状態。
- `test_config_files.py`：3 件とも `if ...exists():` の中で確認しているため、ファイルがなくても通る。見ているファイル（`prompts/okutama_vc.yaml`、`sample/sample_okutama_vc.txt`、`config/ai_models.yaml`）はどれも既に存在せず、一度も確認していなかった。本物のプロンプトファイルを読むテストは他にもない（`test_prompt_utils.py` / `test_llm_config.py` は `tmp_path` の YAML を使う）。
- `db_writer/test_db_access.py`：中身が空。`persist_condition_and_usage` / `save_to_source` のテストにする。モジュール・クラスのデコレータ・クラス内の 3 か所に `django_db` の印があり、`transaction=True` が効いていないので整理する。

### 仕様（`test_config_files.py` の置き換え）
`tests/trail_status/test_config_files.py` を削除し、`tests/trail_status/test_prompt_files.py` を作る。本物のプロンプトファイルを読み、本番のバッチより先に書き間違いに気づけるようにする。本体のコードは変えない。

対象のファイルは `prompt_utils.get_prompt_dir().glob("[0-9][0-9][0-9]_*.yaml")` を名前順に並べたもの（今は `001_okutama_vc.yaml`〜`008_tokyo_akiruno.yaml`）。`example.yaml` / `sample_tanzawa_vc.yaml` / `template.yaml` は含めない。ファイルが増えたら自動で対象になるようにし、ファイル名は直接書かない。

| # | テスト | 期待する結果 |
|---|---|---|
| 6-1 | 対象のファイルが見つかる | 1 件以上ある（`parametrize` の値が空だとテストが skip になり、何も確かめずに通るため、別のテストで確かめる） |
| 6-2 | YAML のキーに書き間違いがない | 対象のファイルに `template.yaml` を加える（個別のファイルの多くは `model` / `temperature` / `thinking_budget` が空で、実際の値はテンプレートが決めるため）。各ファイルを `yaml.safe_load` で読む。トップレベルのキーが `{"prompt", "config"}` に含まれる。`config` があれば、そのキーが `PromptFileConfig.model_fields` の名前か、その alias（`to_camel` の値）に含まれる。`PromptFile` は知らないキーを黙って無視するため、このテストで見つける |
| 6-3 | テンプレートと合わせて `LlmConfig` が作れる | `mock_api_keys` を使う。`PromptFile.load_merged_config(name, url="https://example.com/")` → `LlmConfig.from_file(prompt_file, data="テスト")` が例外なく終わる（temperature の範囲は `LlmConfig` のバリデーションで確かめられる）。`config.model` が `LlmModel` のどれかと一致する（`LlmConfig` のバリデーションは `gemini-` などの頭しか見ないため）。`config.prompt` が空でない、`config.prompt_filename == name` |

- 6-2 と 6-3 は `pytest.mark.parametrize` で対象のファイルごとに 1 件にし、`ids` にファイル名を使う。`template.yaml` は 6-2 だけの対象にする（6-3 はテンプレートと個別のファイルを合わせた結果を見るため）
- `load_site_config` はファイルがないと `example.yaml` をコピーして作るため、対象は必ず glob で見つかったファイルに限る

完成の条件
- docker compose の `web` で `uv run pytest` が全件通る
- 試しに 1 つのファイルの `temperature` を `temprature` に書き換えると 6-2 が失敗することを確かめ、元に戻す（`git diff` でプロンプトファイルに差分が残っていないこと）
- 同じく、`template.yaml` の `temperature` を `temprature` にすると 6-2 が、`model` を `gemini-3-flash-previw` にすると 6-3 が失敗することを確かめ、元に戻す
- 変更したファイルに `ruff check` / `ruff format --check` の新しい違反がない

### 仕様（`test_db_access.py`）
対象は `DbWriter.save_to_source` と `DbWriter.persist_condition_and_usage`（`trail_status/services/db_writer.py`）。本体のコードは変えない。

`tests/trail_status/db_writer/test_db_access.py` を書き直す。

- `django_db` の印はモジュールの `pytestmark = pytest.mark.django_db` の 1 か所だけにする。`transaction=True` は使わない（`atomic()` はテストのトランザクションの中でセーブポイントになるため、ロールバックも確かめられる）
- 空の `TestTrailCondition` は削除する
- `DataSource` はテストファイルの中で `DataSource.objects.create` で作る。項目は `tests/trail_status/views/conftest.py` の `create_sample_data_source` にそろえる。ほかのディレクトリの `conftest.py` は import しない
- `DbWriter` に渡すもの
  - `SourceSchemaSingle`：作った `DataSource` の `id` / `name` / `url1`、`prompt_file=PromptFile(prompt="test")`、`content_hash`
  - `ResultSingle`：`stats` は本物の `LlmStats(TokenStats(...))`（`model` は `LlmModel.GEMINI_2_5_FLASH`）、`config` は `llm_config_factory(LlmModel.GEMINI_2_5_FLASH)`、`extracted_trail_conditions` は `ConditionSchemaAiList`

| # | テスト | 準備 | 期待する結果 |
|---|---|---|---|
| 6-4 | `save_to_source`：内容が変わった | 情報源の `content_hash="old"`、`last_scraped_at` / `last_checked_at` は 2 日前。`ResultSingle(content_changed=True, new_hash="new")` | DB から読み直して、`content_hash == "new"`、`last_scraped_at` と `last_checked_at` が準備の値より新しい |
| 6-5 | `save_to_source`：内容が変わらない | 6-4 と同じ情報源。`ResultSingle(content_changed=False, new_hash="other")`（`content_changed=False` なのに `new_hash` を書き込んでしまう誤りを見分けるため、`"old"` と違う値にする） | `content_hash == "old"`、`last_scraped_at` は準備の値のまま、`last_checked_at` だけが新しい |
| 6-6 | `save_to_source`：結果が例外 | 6-4 と同じ情報源。`DbWriter` の結果に `RuntimeError("失敗")` を渡す | 例外にならず、情報源の 3 項目はどれも準備の値のまま |
| 6-7 | `persist_condition_and_usage`：初回の保存 | `TrailCondition` なし。AI 出力 2 件 | その情報源の `TrailCondition` が 2 件で、どちらも `disabled is True`。`created_at` / `updated_at` / `synced_at` が `None` でない。`ai_model` / `prompt_file` が `config` の値。`LlmUsage` が 1 件で、`prompt_tokens` が `TokenStats` の `input_tokens`、`conditions_extracted == 2`、`success is True`、`cost_usd == Decimal(str(stats.total_fee))`。戻り値は `count == 2`、`created == 2`、`updated == 0` |
| 6-8 | `persist_condition_and_usage`：既存の更新 | `TrailCondition` を 1 件（`status=CLEAR`、`disabled=False`）。AI 出力は山名・登山道名・タイトル・説明が同じで `status=CLOSURE` の 1 件 | `TrailCondition` は 1 件のまま、`status` が `CLOSURE`、`updated_at` が準備の値より新しい。戻り値は `updated == 1`、`created == 0` |
| 6-9 | `persist_condition_and_usage`：途中で失敗したら全部取り消す | 6-7 と同じ準備。`monkeypatch` で `DbWriter._commit_llm_usage` が `RuntimeError` を投げるようにする | `pytest.raises(RuntimeError)`。その情報源の `TrailCondition` も `LlmUsage` も 0 件（`transaction.atomic()` で `TrailCondition` の保存も取り消される） |

完成の条件
- docker compose の `web` で `uv run pytest` が全件通る
- 試しに `persist_condition_and_usage` の `with transaction.atomic():` を外す（中の 2 行はそのまま残す）と 6-9 が失敗することを確かめ、元に戻す（`git diff` で `db_writer.py` に差分が残っていないこと）
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
